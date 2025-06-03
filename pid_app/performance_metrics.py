import numpy as np
from typing import Tuple, Dict
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento del sistema de control"""
    overshoot_percent: float
    settling_time: float
    rise_time: float
    peak_time: float
    steady_state_error: float
    iae: float  # Integral Absolute Error
    ise: float  # Integral Square Error
    itae: float  # Integral Time-weighted Absolute Error


def calculate_step_response_metrics(time: np.ndarray, output: np.ndarray, 
                                  reference: float = 1.0, 
                                  settling_tolerance: float = 0.02) -> PerformanceMetrics:
    """
    Calcula métricas de rendimiento para respuesta al escalón
    
    Args:
        time: Array de tiempo
        output: Array de salida del sistema
        reference: Valor de referencia (por defecto 1.0)
        settling_tolerance: Tolerancia para tiempo de establecimiento (por defecto 2%)
    
    Returns:
        PerformanceMetrics: Objeto con todas las métricas calculadas
    """
    dt = time[1] - time[0] if len(time) > 1 else 1.0
    
    # Valor final estable (promedio de los últimos 10% de puntos)
    final_portion = int(0.9 * len(output))
    steady_state_value = np.mean(output[final_portion:])
    
    # Error de estado estable
    steady_state_error = abs(reference - steady_state_value)
    
    # Overshoot
    peak_value = np.max(output)
    overshoot_percent = max(0, (peak_value - reference) / reference * 100) if reference != 0 else 0
    
    # Tiempo de pico
    peak_idx = np.argmax(output)
    peak_time = time[peak_idx]
    
    # Tiempo de subida (10% a 90% del valor final)
    target_10 = 0.1 * reference
    target_90 = 0.9 * reference
    
    rise_start_idx = np.where(output >= target_10)[0]
    rise_end_idx = np.where(output >= target_90)[0]
    
    if len(rise_start_idx) > 0 and len(rise_end_idx) > 0:
        rise_time = time[rise_end_idx[0]] - time[rise_start_idx[0]]
    else:
        rise_time = 0.0
    
    # Tiempo de establecimiento (dentro del 2% del valor final)
    tolerance_band_upper = steady_state_value + settling_tolerance * reference
    tolerance_band_lower = steady_state_value - settling_tolerance * reference
    
    # Encontrar el último punto que sale de la banda de tolerancia
    outside_band = (output > tolerance_band_upper) | (output < tolerance_band_lower)
    outside_indices = np.where(outside_band)[0]
    
    if len(outside_indices) > 0:
        settling_time = time[outside_indices[-1]]
    else:
        settling_time = 0.0
    
    # Cálculo de errores integrales
    error = reference - output
    abs_error = np.abs(error)
    squared_error = error ** 2
    time_weighted_abs_error = time * abs_error
    
    iae = np.trapz(abs_error, time)
    ise = np.trapz(squared_error, time)
    itae = np.trapz(time_weighted_abs_error, time)
    
    return PerformanceMetrics(
        overshoot_percent=overshoot_percent,
        settling_time=settling_time,
        rise_time=rise_time,
        peak_time=peak_time,
        steady_state_error=steady_state_error,
        iae=iae,
        ise=ise,
        itae=itae
    )


def calculate_disturbance_rejection_metrics(time: np.ndarray, output: np.ndarray) -> Dict[str, float]:
    """
    Calcula métricas específicas para rechazo de perturbaciones
    
    Args:
        time: Array de tiempo
        output: Array de salida del sistema
    
    Returns:
        Dict con métricas de rechazo de perturbaciones
    """
    dt = time[1] - time[0] if len(time) > 1 else 1.0
    
    # Máxima desviación de cero
    max_deviation = np.max(np.abs(output))
    
    # Tiempo para reducir a 5% de la desviación máxima
    target_value = 0.05 * max_deviation
    recovery_indices = np.where(np.abs(output) <= target_value)[0]
    recovery_time = time[recovery_indices[0]] if len(recovery_indices) > 0 else time[-1]
    
    # Energía total de la perturbación (integral del cuadrado)
    disturbance_energy = np.trapz(output ** 2, time)
    
    return {
        'max_deviation': max_deviation,
        'recovery_time': recovery_time,
        'disturbance_energy': disturbance_energy
    } 