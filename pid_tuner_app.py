import streamlit as st
import numpy as np
import pandas as pd
import control as ct
import seaborn as sns
import matplotlib.pyplot as plt

# --- 1. Streamlit UI Design ---
st.title("Interactive PID Tuning Comparison")

# Sidebar for user inputs
st.sidebar.header("Process Model Parameters")
model_type = st.sidebar.selectbox(
    "Choose a Process Model",
    ('First-Order Plus Dead Time (FOPDT)', 'Second-Order System')
)

# Based on the selection, display sliders for the corresponding model parameters
if model_type == 'First-Order Plus Dead Time (FOPDT)':
    st.sidebar.subheader("FOPDT Parameters")
    K = st.sidebar.slider("Process Gain (K)", 0.1, 10.0, 2.0, 0.1)
    tau = st.sidebar.slider("Time Constant (τ)", 1.0, 20.0, 10.0, 0.1)
    theta = st.sidebar.slider("Dead Time (θ)", 0.1, 5.0, 1.5, 0.1)
else:  # Second-Order System
    st.sidebar.subheader("Second-Order System Parameters")
    K = st.sidebar.slider("Process Gain (K)", 0.1, 10.0, 1.5, 0.1)
    wn = st.sidebar.slider("Natural Frequency (ωn)", 0.1, 5.0, 0.5, 0.1)
    zeta = st.sidebar.slider("Damping Ratio (ζ)", 0.1, 2.0, 0.4, 0.1)

# A section for users to input their own PID gains
st.sidebar.subheader("Custom PID Gains")
kp_custom = st.sidebar.number_input("Proportional Gain (Kp)", value=1.0, format="%.4f")
ki_custom = st.sidebar.number_input("Integral Gain (Ki)", value=0.1, format="%.4f")
kd_custom = st.sidebar.number_input("Derivative Gain (Kd)", value=0.01, format="%.4f")

# A button to trigger the simulation
run_button = st.sidebar.button("Run Simulation")

# Main Panel placeholders for the plot and summary table
st.header("Step Response Comparison")
plot_placeholder = st.empty()
st.header("PID Gains Summary")
table_placeholder = st.empty()

# --- 2. Backend Logic & Simulation ---

def get_process_model(model_type, K, tau, theta, wn, zeta):
    """Returns a control.TransferFunction for the selected process model."""
    if model_type == 'First-Order Plus Dead Time (FOPDT)':
        n_pade = 10
        num_pade, den_pade = ct.pade(theta, n_pade)
        pade_tf = ct.tf(num_pade, den_pade)
        process_tf = ct.tf(K, [tau, 1])
        return process_tf * pade_tf
    else:  # Second-Order System
        num = [K * wn**2]
        den = [1, 2 * zeta * wn, wn**2]
        return ct.tf(num, den)

def calculate_pid_gains(K, tau, theta):
    """Calculates PID gains using five tuning rules for an FOPDT model."""
    gains = {}
    if theta <= 1e-6: # Avoid division by zero for non-existent dead time
        return gains

    # 1. Ziegler-Nichols
    Kp_zn = 1.2 * tau / (K * theta)
    Ti_zn = 2.0 * theta
    Td_zn = 0.5 * theta
    gains['Ziegler-Nichols'] = {'Kp': Kp_zn, 'Ki': Kp_zn / Ti_zn, 'Kd': Kp_zn * Td_zn}

    # 2. Cohen-Coon
    R = theta / tau
    Kp_cc = (1.35 / K) * (1/R + 0.185)
    Ti_cc = (2.5 * theta * (1 + 0.185 * R)) / (1 + 0.611 * R)
    Td_cc = (0.37 * theta) / (1 + 0.185 * R)
    gains['Cohen-Coon'] = {'Kp': Kp_cc, 'Ki': Kp_cc / Ti_cc, 'Kd': Kp_cc * Td_cc}

    # 3. IMC (Aggressive)
    Kp_imc = (tau + 0.5 * theta) / (K * theta)
    Ti_imc = tau + 0.5 * theta
    Td_imc = (tau * theta) / (2 * tau + theta)
    gains['IMC'] = {'Kp': Kp_imc, 'Ki': Kp_imc / Ti_imc, 'Kd': Kp_imc * Td_imc}

    # 4. ITAE (Setpoint)
    Kp_itae_sp = (0.965 / K) * (tau / theta)**-0.85
    Ti_itae_sp = tau / (0.796 - 0.1465 * (theta / tau))
    Td_itae_sp = 0.308 * tau * (theta / tau)**0.929
    gains['ITAE (Setpoint)'] = {'Kp': Kp_itae_sp, 'Ki': Kp_itae_sp / Ti_itae_sp, 'Kd': Kp_itae_sp * Td_itae_sp}

    # 5. IAE (Disturbance)
    Kp_iae_dr = (1.435 / K) * (theta / tau)**-0.921
    Ti_iae_dr = (tau / 0.878) * (theta / tau)**0.749
    Td_iae_dr = 0.482 * tau * (theta / tau)**1.137
    gains['IAE (Disturbance)'] = {'Kp': Kp_iae_dr, 'Ki': Kp_iae_dr / Ti_iae_dr, 'Kd': Kp_iae_dr * Td_iae_dr}

    return gains

def run_simulation(process_model, all_gains, t_final):
    """Simulates the step response for each set of PID gains."""
    results = []
    T = np.linspace(0, t_final, 500)

    for method, gains in all_gains.items():
        if gains is None: continue
        Kp, Ki, Kd = gains['Kp'], gains['Ki'], gains['Kd']

        # Create PID Controller Transfer Function
        controller_tf = ct.tf([Kd, Kp, Ki], [1, 0])

        # Calculate Closed-Loop Transfer Function
        closed_loop_tf = ct.feedback(controller_tf * process_model, 1)

        # Run Step Response
        t, y = ct.step_response(closed_loop_tf, T=T)

        # Store results
        df = pd.DataFrame({'Time': t, 'Response': y})
        df['Tuning Method'] = method
        results.append(df)

    return pd.concat(results)

def create_response_plot(df):
    """Creates and returns a seaborn lineplot of the responses."""
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.lineplot(data=df, x='Time', y='Response', hue='Tuning Method', ax=ax)
    ax.set_title('PID Controller Performance Comparison')
    ax.set_xlabel('Time [s]')
    ax.set_ylabel('Process Output')
    ax.grid(True)
    ax.legend(title='Tuning Method')
    return fig

# --- 3. Main Application Logic ---
if run_button:
    # Get the process model based on user selection
    if model_type == 'First-Order Plus Dead Time (FOPDT)':
        process_model = get_process_model(model_type, K, tau, theta, None, None)
        all_gains = calculate_pid_gains(K, tau, theta)
        t_final = 2 * (tau + theta) # Sensible simulation time for FOPDT
    else: # Second-Order System
        process_model = get_process_model(model_type, K, None, None, wn, zeta)
        all_gains = {} # No tuning rules for 2nd order model
        t_final = 15 / (zeta * wn) if zeta * wn > 0 else 30 # Sensible simulation time

    # Add custom gains to the list for simulation
    all_gains['Custom'] = {'Kp': kp_custom, 'Ki': ki_custom, 'Kd': kd_custom}

    if not all_gains or all(g is None for g in all_gains.values()):
        st.error("No valid PID gains to simulate. For FOPDT, ensure dead time is positive.")
    else:
        # Run simulation
        results_df = run_simulation(process_model, all_gains, t_final)

        # Create and display plot
        fig = create_response_plot(results_df)
        plot_placeholder.pyplot(fig)

        # Create and display summary table
        summary_data = {k: v for k, v in all_gains.items() if v is not None}
        summary_df = pd.DataFrame(summary_data).T
        summary_df.columns = ['Kp', 'Ki', 'Kd']
        table_placeholder.dataframe(summary_df.style.format("{:.4f}"))

else:
    # Display initial placeholder content if simulation hasn't been run
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_title("Simulation results will be displayed here")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Process Output")
    ax.grid(True)
    plot_placeholder.pyplot(fig)

    df_dummy = pd.DataFrame({
        'Tuning Method': ['Ziegler-Nichols', 'Cohen-Coon', 'IMC', 'ITAE (Setpoint)', 'IAE (Disturbance)', 'Custom'],
        'Kp': ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', f"{kp_custom:.4f}"],
        'Ki': ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', f"{ki_custom:.4f}"],
        'Kd': ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', f"{kd_custom:.4f}"]
    }).set_index('Tuning Method')
    table_placeholder.dataframe(df_dummy)
