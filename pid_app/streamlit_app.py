import ast
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from control import TransferFunction, forced_response, pole, bode_plot
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from pid import PIDController
from plant import second_order_system, simulate_closed_loop, simulate_disturbance
from performance_metrics import calculate_step_response_metrics, calculate_disturbance_rejection_metrics, PerformanceMetrics
from advanced_systems import get_predefined_systems, ControllerComparison, suggest_pid_parameters

# Configurar página
st.set_page_config(
    page_title="🎛️ Simulador Avanzado de Control PID", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #1f77b4;
        font-size: 3rem;
        margin-bottom: 0;
    }
    .subtitle {
        text-align: center;
        color: #666;
        font-style: italic;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .success-metric {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
    }
    .warning-metric {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
    }
    .error-metric {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-title">🎛️ Simulador Avanzado de Control PID</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Análisis completo de sistemas de control con métricas de rendimiento avanzadas</p>', unsafe_allow_html=True)

# Sidebar mejorado
with st.sidebar:
    st.markdown("### ⚙️ Configuración del Sistema")
    
    # Selección de sistema predefinido
    systems = get_predefined_systems()
    system_options = ["Personalizado"] + list(systems.keys())
    selected_system = st.selectbox(
        "🏭 Tipo de Sistema", 
        system_options,
        help="Selecciona un sistema predefinido o personaliza uno"
    )
    
    if selected_system == "Personalizado":
        st.markdown("#### Parámetros Personalizados")
        system_type = st.selectbox("Tipo", ["Segundo Orden", "Primer Orden", "Integrador"])
        
        if system_type == "Segundo Orden":
            wn = st.number_input("Frecuencia natural ωn", value=1.0, min_value=0.1, max_value=10.0)
            zeta = st.slider("Coeficiente de amortiguamiento ζ", 0.0, 3.0, value=0.7, step=0.1)
            plant = second_order_system(wn, zeta)
            system_params = {'wn': wn, 'zeta': zeta}
        elif system_type == "Primer Orden":
            tau = st.number_input("Constante de tiempo τ", value=1.0, min_value=0.1, max_value=10.0)
            from advanced_systems import create_first_order_system
            plant = create_first_order_system(tau)
            system_params = {'tau': tau}
        else:  # Integrador
            k = st.number_input("Ganancia K", value=1.0, min_value=0.1, max_value=10.0)
            from advanced_systems import create_integrator_system
            plant = create_integrator_system(k)
            system_params = {'k': k}
    else:
        system_config = systems[selected_system]
        plant = system_config.transfer_function
        st.success(f"📋 {system_config.description}")
        system_params = {}
    
    st.markdown("---")
    
    # Configuración de simulación
    st.markdown("### ⏱️ Configuración de Simulación")
    sim_time = st.slider("Tiempo de simulación (s)", 1, 20, 10)
    sim_points = st.slider("Puntos de simulación", 100, 2000, 1000)
    
    st.markdown("---")
    
    # Sintonización del controlador
    st.markdown("### 🎯 Sintonización del Controlador")
    
    # Sugerencias automáticas
    if st.button("🤖 Sugerir Parámetros"):
        if selected_system != "Personalizado":
            # Para sistemas predefinidos, usar parámetros específicos para cada tipo
            if selected_system == 'first_order_fast':
                suggestions = suggest_pid_parameters("first_order", {'tau': 0.5})
            elif selected_system == 'first_order_slow':
                suggestions = suggest_pid_parameters("first_order", {'tau': 3.0})
            elif selected_system in ['underdamped', 'critically_damped', 'overdamped']:
                if selected_system == 'underdamped':
                    suggestions = suggest_pid_parameters("second_order", {'wn': 1.0, 'zeta': 0.3})
                elif selected_system == 'critically_damped':
                    suggestions = suggest_pid_parameters("second_order", {'wn': 1.0, 'zeta': 1.0})
                else:  # overdamped
                    suggestions = suggest_pid_parameters("second_order", {'wn': 1.0, 'zeta': 2.0})
            elif selected_system == 'integrator':
                suggestions = suggest_pid_parameters("integrator", {})
            else:
                # Para sistemas complejos, usar valores conservadores
                suggestions = {'kp': 1.0, 'ki': 0.1, 'kd': 0.1}
        else:
            # Para sistemas personalizados, usar los parámetros específicos
            suggestions = suggest_pid_parameters(system_type.lower().replace(" ", "_"), system_params)
        
        st.session_state.suggested_kp = suggestions['kp']
        st.session_state.suggested_ki = suggestions['ki']
        st.session_state.suggested_kd = suggestions['kd']
        st.success("✅ Parámetros sugeridos aplicados")
    
    tuning_mode = st.selectbox("🛠️ Modo de Sintonización", 
                              ["Manual", "Ziegler-Nichols", "Sugerencias IA"])
    
    # Inicializar valores por defecto
    kp, ki, kd = 1.0, 0.0, 0.0
    
    if tuning_mode == "Manual":
        kp = st.number_input("Kp (Proporcional)", 
                           value=st.session_state.get('suggested_kp', 1.0), 
                           min_value=0.0, max_value=100.0, step=0.1)
        ki = st.number_input("Ki (Integral)", 
                           value=st.session_state.get('suggested_ki', 0.0), 
                           min_value=0.0, max_value=100.0, step=0.1)
        kd = st.number_input("Kd (Derivativo)", 
                           value=st.session_state.get('suggested_kd', 0.0), 
                           min_value=0.0, max_value=100.0, step=0.1)
    
    elif tuning_mode == "Ziegler-Nichols":
        st.markdown("#### Método Ziegler-Nichols")
        ku = st.number_input("Ganancia última Ku", value=2.0, min_value=0.1)
        tu = st.number_input("Período último Tu", value=1.0, min_value=0.1)
        
        method = st.selectbox("Tipo de respuesta", 
                            ["Sin sobreimpulso", "Sobreimpulso mínimo", "Respuesta rápida"])
        
        if method == "Sin sobreimpulso":
            kp, ki, kd = 0.2 * ku, 0.4 * ku / tu, 0.066 * ku * tu
        elif method == "Sobreimpulso mínimo":
            kp, ki, kd = 0.33 * ku, 0.66 * ku / tu, 0.11 * ku * tu
        else:  # Respuesta rápida
            kp, ki, kd = 0.6 * ku, 1.2 * ku / tu, 0.075 * ku * tu
        
        st.write(f"**Kp={kp:.3f}, Ki={ki:.3f}, Kd={kd:.3f}**")
    
    elif tuning_mode == "Sugerencias IA":
        st.markdown("#### Parámetros Sugeridos por IA")
        
        # Obtener sugerencias basadas en el sistema seleccionado
        if selected_system != "Personalizado":
            # Para sistemas predefinidos, usar parámetros específicos para cada tipo
            if selected_system == 'first_order_fast':
                suggestions = suggest_pid_parameters("first_order", {'tau': 0.5})
            elif selected_system == 'first_order_slow':
                suggestions = suggest_pid_parameters("first_order", {'tau': 3.0})
            elif selected_system in ['underdamped', 'critically_damped', 'overdamped']:
                if selected_system == 'underdamped':
                    suggestions = suggest_pid_parameters("second_order", {'wn': 1.0, 'zeta': 0.3})
                elif selected_system == 'critically_damped':
                    suggestions = suggest_pid_parameters("second_order", {'wn': 1.0, 'zeta': 1.0})
                else:  # overdamped
                    suggestions = suggest_pid_parameters("second_order", {'wn': 1.0, 'zeta': 2.0})
            elif selected_system == 'integrator':
                suggestions = suggest_pid_parameters("integrator", {})
            else:
                # Para sistemas complejos, usar valores conservadores
                suggestions = {'kp': 1.0, 'ki': 0.1, 'kd': 0.1}
        else:
            # Para sistemas personalizados, usar los parámetros específicos
            suggestions = suggest_pid_parameters(system_type.lower().replace(" ", "_"), system_params)
        
        # Mostrar explicación del sistema
        st.info(f"🤖 **Sistema detectado:** {selected_system if selected_system != 'Personalizado' else system_type}")
        st.success(f"📊 **Parámetros sugeridos:** Kp={suggestions['kp']:.3f}, Ki={suggestions['ki']:.3f}, Kd={suggestions['kd']:.3f}")
        
        # Permitir ajuste manual de las sugerencias
        st.markdown("##### Ajuste Fino:")
        col1, col2, col3 = st.columns(3)
        with col1:
            kp = st.number_input("Kp", value=suggestions['kp'], min_value=0.0, max_value=100.0, step=0.1, key="ai_kp")
        with col2:
            ki = st.number_input("Ki", value=suggestions['ki'], min_value=0.0, max_value=100.0, step=0.1, key="ai_ki")
        with col3:
            kd = st.number_input("Kd", value=suggestions['kd'], min_value=0.0, max_value=100.0, step=0.1, key="ai_kd")
        
        # Información adicional
        with st.expander("ℹ️ Información sobre las Sugerencias"):
            if selected_system == 'first_order_fast':
                st.write("• Sistema rápido: enfoque en estabilidad con respuesta ágil")
                st.write("• Kp moderado para evitar oscilaciones")
                st.write("• Ki bajo para eliminar error residual sin windup")
            elif selected_system == 'first_order_slow':
                st.write("• Sistema lento: parámetros más agresivos permitidos")
                st.write("• Kp más alto para acelerar respuesta")
                st.write("• Kd para anticipar cambios")
            elif selected_system == 'integrator':
                st.write("• Sistema integrador: evitar acción integral adicional")
                st.write("• Control principalmente proporcional")
                st.write("• Kd para estabilización")
            else:
                st.write("• Parámetros balanceados para rendimiento general")
                st.write("• Basados en criterios de diseño estándar")
        
        if st.button("🔄 Regenerar Sugerencias"):
            st.experimental_rerun()
    
    pid = PIDController(kp, ki, kd)
    
    st.markdown("---")
    
    # Comparación de controladores
    st.markdown("### 📊 Comparación de Controladores")
    enable_comparison = st.checkbox("Activar modo comparación")
    
    if enable_comparison:
        st.markdown("#### Controlador Adicional")
        kp2 = st.number_input("Kp2", value=1.0, key="kp2")
        ki2 = st.number_input("Ki2", value=0.5, key="ki2")
        kd2 = st.number_input("Kd2", value=0.1, key="kd2")

# Layout principal con tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Respuestas del Sistema", 
    "📊 Métricas de Rendimiento", 
    "🔍 Análisis de Frecuencia",
    "⚖️ Comparación",
    "🎛️ Sintonización Interactiva"
])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Respuesta Servo (Seguimiento)")
        
        # Simular respuesta servo
        servo = simulate_closed_loop(pid, 1.0, 0.7, sim_time, sim_points)
        
        # Crear gráfico interactivo con Plotly
        fig_servo = go.Figure()
        fig_servo.add_trace(go.Scatter(
            x=servo.time, 
            y=servo.output,
            mode='lines',
            name='Salida',
            line=dict(color='blue', width=3)
        ))
        fig_servo.add_hline(
            y=1, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Referencia"
        )
        
        fig_servo.update_layout(
            title=f"Respuesta Servo - Kp={kp:.2f}, Ki={ki:.2f}, Kd={kd:.2f}",
            xaxis_title="Tiempo [s]",
            yaxis_title="Amplitud",
            template="plotly_white",
            height=400
        )
        
        st.plotly_chart(fig_servo, use_container_width=True)
        
        # Calcular métricas
        servo_metrics = calculate_step_response_metrics(servo.time, servo.output)
        
    with col2:
        st.markdown("### 🔧 Respuesta Regulatoria (Rechazo de Perturbaciones)")
        
        # Simular respuesta regulatoria
        reg = simulate_disturbance(pid, 1.0, 0.7, sim_time, sim_points)
        
        fig_reg = go.Figure()
        fig_reg.add_trace(go.Scatter(
            x=reg.time, 
            y=reg.output,
            mode='lines',
            name='Salida',
            line=dict(color='green', width=3)
        ))
        fig_reg.add_hline(
            y=0, 
            line_dash="dash", 
            line_color="red",
            annotation_text="Referencia"
        )
        
        fig_reg.update_layout(
            title=f"Respuesta Regulatoria - Kp={kp:.2f}, Ki={ki:.2f}, Kd={kd:.2f}",
            xaxis_title="Tiempo [s]",
            yaxis_title="Amplitud",
            template="plotly_white",
            height=400
        )
        
        st.plotly_chart(fig_reg, use_container_width=True)
        
        # Calcular métricas de perturbación
        reg_metrics = calculate_disturbance_rejection_metrics(reg.time, reg.output)

with tab2:
    st.markdown("### 📊 Análisis Detallado de Rendimiento")
    
    col1, col2, col3 = st.columns(3)
    
    # Métricas principales
    with col1:
        st.markdown("#### 🎯 Métricas de Seguimiento")
        
        # Crear tarjetas de métricas con colores
        overshoot_color = "success-metric" if servo_metrics.overshoot_percent < 20 else "warning-metric" if servo_metrics.overshoot_percent < 50 else "error-metric"
        
        st.markdown(f"""
        <div class="metric-card {overshoot_color}">
            <h4>Sobreimpulso</h4>
            <h2>{servo_metrics.overshoot_percent:.1f}%</h2>
        </div>
        """, unsafe_allow_html=True)
        
        settling_color = "success-metric" if servo_metrics.settling_time < 5 else "warning-metric"
        st.markdown(f"""
        <div class="metric-card {settling_color}">
            <h4>Tiempo de Establecimiento</h4>
            <h2>{servo_metrics.settling_time:.2f}s</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>Tiempo de Subida</h4>
            <h2>{servo_metrics.rise_time:.2f}s</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("#### 🔧 Métricas de Precisión")
        
        sse_color = "success-metric" if servo_metrics.steady_state_error < 0.05 else "warning-metric"
        st.markdown(f"""
        <div class="metric-card {sse_color}">
            <h4>Error de Estado Estable</h4>
            <h2>{servo_metrics.steady_state_error:.4f}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>IAE (Error Absoluto Integral)</h4>
            <h2>{servo_metrics.iae:.3f}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>ISE (Error Cuadrático Integral)</h4>
            <h2>{servo_metrics.ise:.3f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("#### 🛡️ Rechazo de Perturbaciones")
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>Máxima Desviación</h4>
            <h2>{reg_metrics['max_deviation']:.3f}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        recovery_color = "success-metric" if reg_metrics['recovery_time'] < 3 else "warning-metric"
        st.markdown(f"""
        <div class="metric-card {recovery_color}">
            <h4>Tiempo de Recuperación</h4>
            <h2>{reg_metrics['recovery_time']:.2f}s</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h4>Energía de Perturbación</h4>
            <h2>{reg_metrics['disturbance_energy']:.3f}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # Tabla resumen
    st.markdown("#### 📋 Resumen de Métricas")
    metrics_df = pd.DataFrame({
        'Métrica': [
            'Sobreimpulso (%)', 'Tiempo de Subida (s)', 'Tiempo de Establecimiento (s)',
            'Error Estado Estable', 'IAE', 'ISE', 'ITAE',
            'Máx. Desviación', 'Tiempo Recuperación (s)', 'Energía Perturbación'
        ],
        'Valor': [
            f"{servo_metrics.overshoot_percent:.2f}",
            f"{servo_metrics.rise_time:.3f}",
            f"{servo_metrics.settling_time:.3f}",
            f"{servo_metrics.steady_state_error:.4f}",
            f"{servo_metrics.iae:.3f}",
            f"{servo_metrics.ise:.3f}",
            f"{servo_metrics.itae:.3f}",
            f"{reg_metrics['max_deviation']:.3f}",
            f"{reg_metrics['recovery_time']:.3f}",
            f"{reg_metrics['disturbance_energy']:.3f}"
        ],
        'Criterio': [
            '< 20% Excelente, < 50% Bueno',
            '< 2s Rápido',
            '< 5s Bueno',
            '< 0.05 Excelente',
            'Menor es mejor',
            'Menor es mejor',
            'Menor es mejor',
            'Menor es mejor',
            '< 3s Bueno',
            'Menor es mejor'
        ]
    })
    st.dataframe(metrics_df, use_container_width=True)

with tab3:
    st.markdown("### 🔍 Análisis de Frecuencia")
    
    # Crear sistema en lazo cerrado
    try:
        if kp == 0 and ki == 0 and kd == 0:
            st.warning("⚠️ Todos los parámetros PID son cero - Sistema en lazo abierto")
            cl_system = plant
        else:
            C = TransferFunction([kd, kp, ki], [1, 0])
            cl_system = (C * plant).feedback(1)
        
        # Análisis de polos
        st.markdown("#### 📍 Análisis de Polos")
        poles = pole(cl_system)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Mapa de polos
            real_parts = np.real(poles)
            imag_parts = np.imag(poles)
            
            fig_poles = go.Figure()
            fig_poles.add_trace(go.Scatter(
                x=real_parts,
                y=imag_parts,
                mode='markers',
                marker=dict(size=12, color='red', symbol='x'),
                name='Polos'
            ))
            
            # Línea de estabilidad
            fig_poles.add_vline(x=0, line_dash="dash", line_color="black", 
                              annotation_text="Límite de Estabilidad")
            
            fig_poles.update_layout(
                title="Mapa de Polos del Sistema",
                xaxis_title="Parte Real",
                yaxis_title="Parte Imaginaria",
                template="plotly_white",
                height=400
            )
            
            st.plotly_chart(fig_poles, use_container_width=True)
        
        with col2:
            st.markdown("#### 🔢 Información de Polos")
            
            # Verificar estabilidad
            is_stable = np.all(np.real(poles) < 0)
            stability_color = "🟢" if is_stable else "🔴"
            stability_text = "ESTABLE" if is_stable else "INESTABLE"
            
            st.markdown(f"**Estado: {stability_color} {stability_text}**")
            
            # Mostrar polos
            poles_df = pd.DataFrame({
                'Polo': [f"p{i+1}" for i in range(len(poles))],
                'Valor': [f"{p:.4f}" for p in poles],
                'Parte Real': [f"{np.real(p):.4f}" for p in poles],
                'Parte Imaginaria': [f"{np.imag(p):.4f}" for p in poles]
            })
            st.dataframe(poles_df, use_container_width=True)
            
            # Frecuencia natural y amortiguamiento (para polos complejos)
            complex_poles = poles[np.abs(np.imag(poles)) > 1e-6]
            if len(complex_poles) > 0:
                for i, p in enumerate(complex_poles):
                    wn = abs(p)
                    zeta = -np.real(p) / wn if wn > 0 else 0
                    st.write(f"**Polo complejo {i+1}:** ωn={wn:.3f}, ζ={zeta:.3f}")
    
    except Exception as e:
        st.error(f"Error en análisis de frecuencia: {e}")

with tab4:
    if enable_comparison:
        st.markdown("### ⚖️ Comparación de Controladores")
        
        # Crear segundo controlador
        pid2 = PIDController(kp2, ki2, kd2)
        
        # Simular ambos controladores
        servo1 = simulate_closed_loop(pid, 1.0, 0.7, sim_time, sim_points)
        servo2 = simulate_closed_loop(pid2, 1.0, 0.7, sim_time, sim_points)
        
        # Gráfico comparativo
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(
            x=servo1.time, y=servo1.output,
            mode='lines', name=f'PID 1 (Kp={kp:.1f}, Ki={ki:.1f}, Kd={kd:.1f})',
            line=dict(color='blue', width=3)
        ))
        fig_comp.add_trace(go.Scatter(
            x=servo2.time, y=servo2.output,
            mode='lines', name=f'PID 2 (Kp={kp2:.1f}, Ki={ki2:.1f}, Kd={kd2:.1f})',
            line=dict(color='red', width=3)
        ))
        fig_comp.add_hline(y=1, line_dash="dash", line_color="gray", 
                          annotation_text="Referencia")
        
        fig_comp.update_layout(
            title="Comparación de Respuestas",
            xaxis_title="Tiempo [s]",
            yaxis_title="Amplitud",
            template="plotly_white",
            height=500
        )
        
        st.plotly_chart(fig_comp, use_container_width=True)
        
        # Métricas comparativas
        metrics1 = calculate_step_response_metrics(servo1.time, servo1.output)
        metrics2 = calculate_step_response_metrics(servo2.time, servo2.output)
        
        comparison_df = pd.DataFrame({
            'Métrica': ['Sobreimpulso (%)', 'Tiempo Subida (s)', 'Tiempo Establecimiento (s)', 'Error Estado Estable', 'IAE'],
            'PID 1': [
                f"{metrics1.overshoot_percent:.2f}",
                f"{metrics1.rise_time:.3f}",
                f"{metrics1.settling_time:.3f}",
                f"{metrics1.steady_state_error:.4f}",
                f"{metrics1.iae:.3f}"
            ],
            'PID 2': [
                f"{metrics2.overshoot_percent:.2f}",
                f"{metrics2.rise_time:.3f}",
                f"{metrics2.settling_time:.3f}",
                f"{metrics2.steady_state_error:.4f}",
                f"{metrics2.iae:.3f}"
            ]
        })
        
        st.markdown("#### 📊 Comparación de Métricas")
        st.dataframe(comparison_df, use_container_width=True)
        
        # Determinar ganador
        winner_metrics = {
            'Menor sobreimpulso': 1 if metrics1.overshoot_percent < metrics2.overshoot_percent else 2,
            'Menor tiempo de subida': 1 if metrics1.rise_time < metrics2.rise_time else 2,
            'Menor tiempo de establecimiento': 1 if metrics1.settling_time < metrics2.settling_time else 2,
            'Menor error estado estable': 1 if metrics1.steady_state_error < metrics2.steady_state_error else 2,
            'Menor IAE': 1 if metrics1.iae < metrics2.iae else 2
        }
        
        pid1_wins = sum(1 for winner in winner_metrics.values() if winner == 1)
        pid2_wins = sum(1 for winner in winner_metrics.values() if winner == 2)
        
        if pid1_wins > pid2_wins:
            st.success(f"🏆 **PID 1 es mejor** ({pid1_wins}/{len(winner_metrics)} métricas)")
        elif pid2_wins > pid1_wins:
            st.success(f"🏆 **PID 2 es mejor** ({pid2_wins}/{len(winner_metrics)} métricas)")
        else:
            st.info("🤝 **Empate** - Ambos controladores tienen rendimiento similar")
            
    else:
        st.info("💡 Activa el modo comparación en la barra lateral para comparar diferentes configuraciones de controladores")

with tab5:
    st.markdown("### 🎛️ Sintonización Interactiva en Tiempo Real")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### ⚡ Controles Rápidos")
        
        # Sliders para ajuste rápido
        kp_slider = st.slider("Kp", 0.0, 10.0, float(kp), 0.1, key="kp_slider")
        ki_slider = st.slider("Ki", 0.0, 5.0, float(ki), 0.1, key="ki_slider")
        kd_slider = st.slider("Kd", 0.0, 2.0, float(kd), 0.1, key="kd_slider")
        
        # Aplicar cambios
        if st.button("🔄 Actualizar Respuesta"):
            st.experimental_rerun()
    
    with col2:
        # Simulación en tiempo real con los sliders
        pid_interactive = PIDController(kp_slider, ki_slider, kd_slider)
        servo_interactive = simulate_closed_loop(pid_interactive, 1.0, 0.7, sim_time, sim_points)
        
        fig_interactive = go.Figure()
        fig_interactive.add_trace(go.Scatter(
            x=servo_interactive.time, 
            y=servo_interactive.output,
            mode='lines',
            name='Respuesta Actual',
            line=dict(color='purple', width=3)
        ))
        fig_interactive.add_hline(y=1, line_dash="dash", line_color="red", 
                                annotation_text="Referencia")
        
        fig_interactive.update_layout(
            title=f"Sintonización en Tiempo Real - Kp={kp_slider:.1f}, Ki={ki_slider:.1f}, Kd={kd_slider:.1f}",
            xaxis_title="Tiempo [s]",
            yaxis_title="Amplitud",
            template="plotly_white",
            height=400
        )
        
        st.plotly_chart(fig_interactive, use_container_width=True)
        
        # Métricas rápidas
        metrics_interactive = calculate_step_response_metrics(servo_interactive.time, servo_interactive.output)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Sobreimpulso", f"{metrics_interactive.overshoot_percent:.1f}%")
        with col_b:
            st.metric("Tiempo Subida", f"{metrics_interactive.rise_time:.2f}s")
        with col_c:
            st.metric("Tiempo Establecimiento", f"{metrics_interactive.settling_time:.2f}s")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <h4>🎛️ Simulador Avanzado de Control PID</h4>
    <p>Desarrollado con ❤️ usando Streamlit • Control Systems • Plotly</p>
    <p><strong>Funcionalidades:</strong> Análisis de rendimiento • Comparación de controladores • Sintonización interactiva • Sistemas predefinidos</p>
</div>
""", unsafe_allow_html=True)

