# 🎛️ Proyecto de Control PID

Este proyecto demuestra un controlador PID simple aplicado a un sistema de segundo orden usando una interfaz web de Streamlit. Los usuarios pueden ajustar parámetros del controlador de manera interactiva y visualizar tanto respuestas servo como regulatorias. La aplicación también proporciona información básica de colocación de polos y estabilidad.

## 📋 Requisitos

Instale las dependencias necesarias:

```bash
pip install -r requirements.txt
```

O manualmente:

```bash
pip install streamlit control numpy matplotlib scipy
```

## 🚀 Ejecución

Ejecute la aplicación Streamlit desde la raíz del repositorio:

```bash
streamlit run pid_app/streamlit_app.py
```

Esto abrirá una ventana del navegador mostrando widgets para ajustar parámetros y graficar la respuesta.

## ✨ Características

- **Sintonización Manual**: Ajuste manual de parámetros Kp, Ki, Kd
- **Método Ziegler-Nichols**: Sintonización automática basada en parámetros críticos
- **Colocación de Polos**: Cálculo automático de parámetros PID para polos deseados
- **Visualización**: Gráficos de respuesta servo y regulatoria
- **Análisis de Estabilidad**: Visualización de polos en lazo cerrado

## 🔧 Estructura del Proyecto

- `pid_app/streamlit_app.py`: Aplicación principal de Streamlit
- `pid_app/pid.py`: Implementación del controlador PID
- `pid_app/plant.py`: Definición del sistema de segundo orden y simulaciones
- `requirements.txt`: Dependencias del proyecto
