from dataclasses import dataclass
import numpy as np
from control import TransferFunction, forced_response


def second_order_system(wn: float, zeta: float) -> TransferFunction:
    """Return a second-order TransferFunction"""
    num = [1.0]
    den = [1.0, 2 * zeta * wn, wn ** 2]
    return TransferFunction(num, den)


@dataclass
class SimulationResult:
    time: np.ndarray
    output: np.ndarray


def simulate_closed_loop(pid, wn: float, zeta: float, t_end: float = 10.0, n: int = 500):
    plant = second_order_system(wn, zeta)
    # closed-loop transfer function for servo control: C*G/(1+C*G)
    C = TransferFunction([pid.kd, pid.kp, pid.ki], [1, 0])
    closed_loop = (C * plant).feedback(1)
    t = np.linspace(0, t_end, n)
    # Entrada escalón unitario
    u = np.ones_like(t)
    t, y = forced_response(closed_loop, T=t, U=u)
    return SimulationResult(t, y)


def simulate_disturbance(pid, wn: float, zeta: float, t_end: float = 10.0, n: int = 500):
    plant = second_order_system(wn, zeta)
    C = TransferFunction([pid.kd, pid.kp, pid.ki], [1, 0])
    # output due to load disturbance at plant input: G/(1+C*G)
    disturbance_tf = plant.feedback(C)
    t = np.linspace(0, t_end, n)
    # Entrada escalón unitario como perturbación
    u = np.ones_like(t)
    t, y = forced_response(disturbance_tf, T=t, U=u)
    return SimulationResult(t, y)
