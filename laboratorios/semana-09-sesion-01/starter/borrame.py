import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# CONFIGURACIÓN DEL RELOJ DE 24 HORAS
# =====================================================================
# Función de mapeo: 24 horas -> ángulo en [0, 2pi)
# (00:00 en x=1, y=0 avanzando en sentido antihorario estándar)
def hour_to_angle(h):
    return (2.0 * np.pi * (h % 24.0)) / 24.0

# Puntos de interés para los dos rangos (ambos de 2 horas)
# Rango A: 23:00 a 01:00
# Rango B: 04:00 a 06:00
horas_interes = np.array([23.0, 1.0, 4.0, 6.0])
etiquetas_interes = ['23:00', '01:00', '04:00', '06:00']
colores_puntos = ['#d95f02', '#1f78b4', '#2ca02c', '#17becf']

thetas = hour_to_angle(horas_interes)
x = np.cos(thetas)
y = np.sin(thetas)

fig, ax = plt.subplots(figsize=(8.5, 8.5))

# 1. Esfera base del reloj (Círculo unitario r = 1)
t_circ = np.linspace(0, 2 * np.pi, 500)
ax.plot(np.cos(t_circ), np.sin(t_circ), color='silver', linestyle='-', linewidth=1.5, zorder=1)
ax.axhline(0, color='gray', lw=0.6, alpha=0.3)
ax.axvline(0, color='gray', lw=0.6, alpha=0.3)

# 2. Marcas horarias del reloj de 24 horas
for h in range(24):
    th = hour_to_angle(h)
    xh, yh = np.cos(th), np.sin(th)
    
    # Marcas principales cada 6 horas y secundarias para las demás
    if h in [0, 6, 12, 18]:
        ax.plot([0.93 * xh, xh], [0.93 * yh, yh], color='dimgray', lw=1.8)
        lbl_hora = f"{h:02d}:00"
        ax.text(1.16 * xh, 1.16 * yh, lbl_hora, ha='center', va='center', 
                fontsize=9.5, fontweight='bold', color='black')
    else:
        ax.plot([0.96 * xh, xh], [0.96 * yh, yh], color='darkgray', lw=1.0)
        # Etiquetas tenues en horas pares restantes para no saturar
        if h % 2 == 0 and h not in [4, 6]:
            ax.text(1.10 * xh, 1.10 * yh, f"{h}h", ha='center', va='center', 
                    fontsize=7.5, color='gray')

# 3. Puntos de los rangos evaluados
for xi, yi, lbl, col in zip(x, y, etiquetas_interes, colores_puntos):
    ax.scatter(xi, yi, color=col, s=110, zorder=6)
    ax.text(1.15 * xi, 1.15 * yi, lbl, ha='center', va='center', 
            fontweight='bold', color=col, fontsize=9.5, zorder=7)

# =====================================================================
# RANGO A: 23:00 a 01:00 (Naranja / Rojo)
# =====================================================================
# Arco continuo sobre la circunferencia (cruza medianoche: -pi/12 a pi/12)
t_arc_A = np.linspace(thetas[0] - 2 * np.pi, thetas[1], 100)
ax.plot(np.cos(t_arc_A), np.sin(t_arc_A), color='#e41a1c', linestyle='-', lw=4.0, zorder=3,
        label=r'Arco A (23h–01h, continuo): $s = \Delta\theta \approx 0.524$ rad')

# Cuerda suave con puntos por el interior
ax.plot([x[0], x[1]], [y[0], y[1]], color='#e41a1c', linestyle=':', lw=2.0, alpha=0.45, zorder=2,
        label=r'Cuerda A (23h–01h, suave): $d = 2|\sin(\Delta\theta/2)| \approx 0.518$')

# =====================================================================
# RANGO B: 04:00 a 06:00 (Verde / Teal) - Separado para no toparse
# =====================================================================
# Arco continuo sobre la circunferencia
t_arc_B = np.linspace(thetas[2], thetas[3], 100)
ax.plot(np.cos(t_arc_B), np.sin(t_arc_B), color='#2ca02c', linestyle='-', lw=4.0, zorder=3,
        label=r'Arco B (04h–06h, continuo): $s = \Delta\theta \approx 0.524$ rad')

# Cuerda suave con puntos por el interior
ax.plot([x[2], x[3]], [y[2], y[3]], color='#2ca02c', linestyle=':', lw=2.0, alpha=0.45, zorder=2,
        label=r'Cuerda B (04h–06h, suave): $d = 2|\sin(\Delta\theta/2)| \approx 0.518$')

# Configuración final de la vista
ax.set_xlim(-1.4, 1.4)
ax.set_ylim(-1.4, 1.4)
ax.set_aspect('equal')
ax.set_title("Topología Circular en Reloj de 24 Horas ($S^1$, $r=1$)\nArcos continuos sobre la curva vs. Cuerdas punteadas interiores",
             fontsize=12, fontweight='bold', pad=20)
ax.set_xlabel(r"Eje $\cos(\theta)$")
ax.set_ylabel(r"Eje $\sin(\theta)$")
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), frameon=True, fontsize=8.5, ncol=1)
ax.grid(True, alpha=0.2)

plt.tight_layout()
plt.show()
