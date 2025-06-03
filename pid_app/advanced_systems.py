import numpy as np
from control import TransferFunction, forced_response, step_response
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class SystemConfig:
    """Configuración de un sistema"""
    name: str
    transfer_function: TransferFunction
    description: str


def create_first_order_system(tau: float, k: float = 1.0) -> TransferFunction:
    """
    Crea un sistema de primer orden: K/(τs + 1)
    
    Args:
        tau: Constante de tiempo
        k: Ganancia estática
    """
    return TransferFunction([k], [tau, 1])


def create_second_order_system(wn: float, zeta: float, k: float = 1.0) -> TransferFunction:
    """
    Crea un sistema de segundo orden: K*ωn²/(s² + 2ζωns + ωn²)
    
    Args:
        wn: Frecuencia natural
        zeta: Coeficiente de amortiguamiento
        k: Ganancia estática
    """
    num = [k * wn**2]
    den = [1, 2*zeta*wn, wn**2]
    return TransferFunction(num, den)


def create_integrator_system(k: float = 1.0) -> TransferFunction:
    """
    Crea un sistema integrador: K/s
    
    Args:
        k: Ganancia
    """
    return TransferFunction([k], [1, 0])


def create_delay_system(delay: float, tau: float = 1.0, k: float = 1.0) -> TransferFunction:
    """
    Aproxima un sistema con retardo usando aproximación de Padé
    
    Args:
        delay: Tiempo de retardo
        tau: Constante de tiempo del sistema
        k: Ganancia estática
    """
    # Aproximación de Padé de primer orden para el retardo
    # e^(-Ls) ≈ (1 - Ls/2) / (1 + Ls/2)
    
    # Sistema sin retardo
    base_system = create_first_order_system(tau, k)
    
    # Aproximación de Padé
    delay_num = [-delay/2, 1]
    delay_den = [delay/2, 1]
    delay_tf = TransferFunction(delay_num, delay_den)
    
    return base_system * delay_tf


def create_high_order_system(poles: List[float], zeros: List[float] = None, k: float = 1.0) -> TransferFunction:
    """
    Crea un sistema de orden superior especificando polos y ceros
    
    Args:
        poles: Lista de polos (pueden ser complejos)
        zeros: Lista de ceros (opcional)
        k: Ganancia
    """
    if zeros is None:
        zeros = []
    
    # Construir polinomios
    den_poly = np.poly(poles)
    
    if zeros:
        num_poly = k * np.poly(zeros)
    else:
        num_poly = [k]
    
    return TransferFunction(num_poly, den_poly)


def get_predefined_systems() -> Dict[str, SystemConfig]:
    """
    Retorna un diccionario con sistemas predefinidos para pruebas
    """
    systems = {}
    
    # Sistema de primer orden rápido
    systems['first_order_fast'] = SystemConfig(
        name="Primer Orden Rápido",
        transfer_function=create_first_order_system(0.5),
        description="Sistema de primer orden con τ=0.5s"
    )
    
    # Sistema de primer orden lento
    systems['first_order_slow'] = SystemConfig(
        name="Primer Orden Lento",
        transfer_function=create_first_order_system(3.0),
        description="Sistema de primer orden con τ=3.0s"
    )
    
    # Sistema subamortiguado
    systems['underdamped'] = SystemConfig(
        name="Segundo Orden Subamortiguado",
        transfer_function=create_second_order_system(1.0, 0.3),
        description="ζ=0.3, ωn=1.0 rad/s"
    )
    
    # Sistema críticamente amortiguado
    systems['critically_damped'] = SystemConfig(
        name="Segundo Orden Crítico",
        transfer_function=create_second_order_system(1.0, 1.0),
        description="ζ=1.0, ωn=1.0 rad/s"
    )
    
    # Sistema sobreamortiguado
    systems['overdamped'] = SystemConfig(
        name="Segundo Orden Sobreamortiguado",
        transfer_function=create_second_order_system(1.0, 2.0),
        description="ζ=2.0, ωn=1.0 rad/s"
    )
    
    # Sistema integrador
    systems['integrator'] = SystemConfig(
        name="Integrador Puro",
        transfer_function=create_integrator_system(1.0),
        description="1/s - Requiere acción integral"
    )
    
    # Sistema con retardo
    systems['delay_system'] = SystemConfig(
        name="Sistema con Retardo",
        transfer_function=create_delay_system(0.5, 1.0),
        description="Sistema de primer orden con retardo de 0.5s"
    )
    
    # Sistema de orden superior
    poles = [-1, -2, -3, -0.5+1j, -0.5-1j]
    systems['high_order'] = SystemConfig(
        name="Sistema de Orden Superior",
        transfer_function=create_high_order_system(poles),
        description="Sistema de 5to orden con polos complejos"
    )
    
    return systems


class ControllerComparison:
    """Clase para comparar diferentes configuraciones de controladores"""
    
    def __init__(self, plant: TransferFunction):
        self.plant = plant
        self.results = {}
    
    def add_controller(self, name: str, kp: float, ki: float, kd: float):
        """Agregar un controlador a la comparación"""
        from pid import PIDController
        
        controller = PIDController(kp, ki, kd)
        
        # Simular respuesta
        C = TransferFunction([kd, kp, ki], [1, 0])
        closed_loop = (C * self.plant).feedback(1)
        
        t = np.linspace(0, 10, 1000)
        u = np.ones_like(t)
        t, y = forced_response(closed_loop, T=t, U=u)
        
        self.results[name] = {
            'time': t,
            'output': y,
            'controller': controller,
            'closed_loop': closed_loop
        }
    
    def get_comparison_data(self) -> Dict:
        """Obtener datos para comparación"""
        return self.results


def suggest_pid_parameters(system_type: str, system_params: Dict) -> Dict[str, float]:
    """
    Sugerir parámetros PID iniciales basados en el tipo de sistema
    
    Args:
        system_type: Tipo de sistema ('first_order', 'second_order', etc.)
        system_params: Parámetros del sistema
    
    Returns:
        Diccionario con parámetros PID sugeridos
    """
    suggestions = {}
    
    if system_type == 'first_order':
        tau = system_params.get('tau', 1.0)
        # Reglas empíricas para primer orden
        suggestions = {
            'kp': 1.0 / tau,
            'ki': 1.0 / (2 * tau**2),
            'kd': tau / 4
        }
    
    elif system_type == 'second_order':
        wn = system_params.get('wn', 1.0)
        zeta = system_params.get('zeta', 0.5)
        
        # Basado en criterios de diseño estándar
        if zeta < 0.7:  # Subamortiguado
            suggestions = {
                'kp': 2 * zeta * wn,
                'ki': wn**2,
                'kd': 1.0
            }
        else:  # Sobreamortiguado o crítico
            suggestions = {
                'kp': wn,
                'ki': wn**2 / 2,
                'kd': 2 * zeta / wn
            }
    
    elif system_type == 'integrator':
        # Para integradores, evitar acción integral adicional
        suggestions = {
            'kp': 1.0,
            'ki': 0.0,
            'kd': 0.5
        }
    
    else:
        # Valores conservadores por defecto
        suggestions = {
            'kp': 1.0,
            'ki': 0.1,
            'kd': 0.1
        }
    
    return suggestions 