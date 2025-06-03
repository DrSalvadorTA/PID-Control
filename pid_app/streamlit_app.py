import ast
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from control import TransferFunction, forced_response, pole

from .pid import PIDController
from .plant import second_order_system, simulate_closed_loop, simulate_disturbance


st.set_page_config(page_title="PID Second Order Simulator")

st.title("PID Controller Simulator")

with st.sidebar:
    st.header("Plant Parameters")
    wn = st.number_input("Natural frequency ωn", value=1.0, min_value=0.1)
    zeta = st.slider("Damping ratio ζ", 0.0, 2.0, value=0.2)

    st.header("Tuning")
    tuning_mode = st.selectbox("Mode", ["Manual", "Ziegler-Nichols"], index=0)
    if tuning_mode == "Manual":
        kp = st.number_input("Kp", value=1.0)
        ki = st.number_input("Ki", value=0.0)
        kd = st.number_input("Kd", value=0.0)
    else:
        ku = st.number_input("Ultimate gain Ku", value=1.0)
        tu = st.number_input("Ultimate period Tu", value=1.0)
        kp = 0.6 * ku
        ki = 2 * kp / tu
        kd = kp * tu / 8
        st.write(f"Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}")

    pid = PIDController(kp, ki, kd)

    st.header("Pole Placement")
    p1 = st.text_input("Pole p1", value="-1.0")
    p2 = st.text_input("Pole p2", value="-1.0+1j")
    p3 = st.text_input("Pole p3", value="-1.0-1j")
    if st.button("Compute PID for poles"):
        try:
            poles = [complex(ast.literal_eval(p)) for p in (p1, p2, p3)]
            coeffs = np.poly(poles)
            a = 2 * zeta * wn
            b = wn ** 2
            pid.kd = coeffs[1] - a
            pid.kp = coeffs[2] - b
            pid.ki = coeffs[3]
            st.success(f"PID set to Kp={pid.kp:.3f}, Ki={pid.ki:.3f}, Kd={pid.kd:.3f}")
        except Exception as exc:
            st.error(f"Failed to compute PID: {exc}")


st.subheader("Servo Control Response")
servo = simulate_closed_loop(pid, wn, zeta)
fig1, ax1 = plt.subplots()
ax1.plot(servo.time, servo.output)
ax1.set_xlabel("Time [s]")
ax1.set_ylabel("Output")
ax1.grid(True)
st.pyplot(fig1)

st.subheader("Regulatory Control Response (Load Disturbance)")
reg = simulate_disturbance(pid, wn, zeta)
fig2, ax2 = plt.subplots()
ax2.plot(reg.time, reg.output)
ax2.set_xlabel("Time [s]")
ax2.set_ylabel("Output")
ax2.grid(True)
st.pyplot(fig2)

# Stability analysis
st.subheader("Closed-loop Poles")
C = TransferFunction([pid.kd, pid.kp, pid.ki], [1, 0])
plant = second_order_system(wn, zeta)
cl = (C * plant).feedback(1)
cl_poles = pole(cl)
st.write(cl_poles)

