"""Run a target-blind, 50-compound Gemini benchmark against MLflow models."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.datos import load_local_environment, load_snapshot
from src.experiments import EXPERIMENT_NAME, WORKFLOW_VERSION, configure_tracking
from src.llm_benchmark import (
    DEFAULT_MODEL,
    PROMPT_VERSION,
    build_prediction_prompt,
    request_gemini_prediction,
)
from src.pipeline import clear_feature_caches, model_inputs, valid_smiles_mask
from src.splits import create_or_load_holdout

SEED = 42
SAMPLE_SIZE = 50
MODEL_NAME = "qsrr-predict-modelo"


def main() -> None:
    load_local_environment()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Configure GEMINI_API_KEY in the local environment or ignored "
            "psets/pset-03/.env before running the authorized API benchmark."
        )

    frame, data_metadata = load_snapshot()
    valid = valid_smiles_mask(frame)
    modeling_data = frame.loc[
        valid & frame["inchikey"].notna()
    ].reset_index(drop=True)
    _, holdout, split_metadata = create_or_load_holdout(
        modeling_data,
        source_sha256=data_metadata["sha256"],
    )
    sample = (
        holdout.sort_values("hecho_id", kind="mergesort")
        .drop_duplicates("inchikey")
        .sample(
            n=min(SAMPLE_SIZE, holdout["inchikey"].nunique()),
            random_state=SEED,
        )
        .sort_values("hecho_id", kind="mergesort")
        .reset_index(drop=True)
    )
    if sample.empty:
        raise ValueError("The grouped holdout has no valid compounds to benchmark")

    X_sample, y_sample, _ = model_inputs(sample)
    champion = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@champion")
    challenger = mlflow.sklearn.load_model(f"models:/{MODEL_NAME}@challenger")
    champion_predictions = champion.predict(X_sample)
    challenger_predictions = challenger.predict(X_sample)
    clear_feature_caches()

    sample_predictions = []
    prompt_tokens = []
    output_tokens = []
    token_totals = {}
    configure_tracking()
    run_name = f"gemini-zero-shot-{DEFAULT_MODEL}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.set_tags(
            {
                "phase": "llm_benchmark",
                "model_family": "gemini_zero_shot",
                "workflow_version": WORKFLOW_VERSION,
                "target_labels_sent_to_provider": "false",
                "external_data_authorized": "public_repoRT_holdout_sample",
            }
        )
        mlflow.log_params(
            {
                "provider": "Google Gemini API",
                "model": DEFAULT_MODEL,
                "benchmark_type": "zero-shot",
                "prompt_version": PROMPT_VERSION,
                "sample_size": len(sample),
                "unique_compounds": int(sample["inchikey"].nunique()),
                "random_state": SEED,
                "data_sha256": data_metadata["sha256"],
                "holdout_split_hash": split_metadata["model_rows_hash"],
                "target_labels_sent_to_provider": False,
            }
        )
        for index, (_, row) in enumerate(sample.iterrows(), start=1):
            result = request_gemini_prediction(
                build_prediction_prompt(row),
                api_key=api_key,
                model=DEFAULT_MODEL,
            )
            sample_predictions.append(float(result["prediction"]))
            prompt_tokens.append(result["prompt_tokens"])
            output_tokens.append(result["output_tokens"])
            print(f"Gemini predictions: {index}/{len(sample)}")

        predictions = pd.DataFrame(
            {
                "hecho_id": sample["hecho_id"].astype(str),
                "inchikey": sample["inchikey"].astype(str),
                "actual_retention_min": y_sample.to_numpy(),
                "gemini_prediction_min": sample_predictions,
                "champion_prediction_min": champion_predictions,
                "challenger_prediction_min": challenger_predictions,
            }
        )
        metrics = {}
        for label, column in (
            ("gemini", "gemini_prediction_min"),
            ("champion", "champion_prediction_min"),
            ("challenger", "challenger_prediction_min"),
        ):
            metrics[f"{label}_rmse_min"] = float(
                root_mean_squared_error(
                    predictions["actual_retention_min"], predictions[column]
                )
            )
            metrics[f"{label}_mae_min"] = float(
                mean_absolute_error(
                    predictions["actual_retention_min"], predictions[column]
                )
            )
        mlflow.log_metrics(metrics)
        for token_name, values in (
            ("prompt_tokens_total", prompt_tokens),
            ("output_tokens_total", output_tokens),
        ):
            known_values = [value for value in values if value is not None]
            token_totals[token_name] = (
                sum(known_values) if known_values else None
            )
        mlflow.log_metrics(
            {
                f"gemini_{name}": float(value)
                for name, value in token_totals.items()
                if value is not None
            }
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        predictions_path = PROJECT_ROOT / "docs" / (
            f"llm_benchmark_predictions_{timestamp}.csv"
        )
        metrics_path = PROJECT_ROOT / "docs" / (
            f"llm_benchmark_metrics_{timestamp}.json"
        )
        predictions.to_csv(predictions_path, index=False)
        report = {
            "provider": "Google Gemini API",
            "model": DEFAULT_MODEL,
            "benchmark_type": "zero-shot",
            "prompt_version": PROMPT_VERSION,
            "sample_size": len(sample),
            "unique_compounds": int(sample["inchikey"].nunique()),
            "random_state": SEED,
            "data_sha256": data_metadata["sha256"],
            "holdout_split_hash": split_metadata["model_rows_hash"],
            "target_labels_sent_to_provider": False,
            "api_calls": len(sample),
            **token_totals,
            "mlflow_run_id": run.info.run_id,
            "metrics": metrics,
        }
        metrics_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        mlflow.log_artifact(str(predictions_path), artifact_path="llm_benchmark")
        mlflow.log_artifact(str(metrics_path), artifact_path="llm_benchmark")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
