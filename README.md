# 🧠 Detector de Proposiciones y Árboles Semánticos

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Interfaz-Tkinter-orange?style=for-the-badge" alt="Tkinter">
  <img src="https://img.shields.io/badge/Lógica-Proposicional-8A2BE2?style=for-the-badge" alt="Lógica proposicional">
  <img src="https://img.shields.io/badge/Proyecto-Académico-2EA44F?style=for-the-badge" alt="Proyecto académico">
</p>

## 📌 Descripción

Este proyecto consiste en una aplicación de escritorio desarrollada en **Python** para la identificación de proposiciones y relaciones lógicas a partir de oraciones escritas en lenguaje natural.

El sistema permite construir una base de conocimientos, identificar conectores lógicos y representar gráficamente un **árbol semántico o tableau semántico**, mediante el cual se exploran diferentes mundos posibles, se detectan contradicciones y se identifican las ramas que permanecen abiertas.

El objetivo es facilitar el estudio de la lógica proposicional y comprender cómo las premisas y reglas de una base de conocimientos restringen las interpretaciones posibles.

## ✨ Características principales

- 📝 **Entrada de oraciones:** permite introducir proposiciones y reglas mediante texto.
- 🔎 **Identificación de proposiciones:** asigna identificadores como `x[1]`, `x[2]` y `x[3]`.
- 🔗 **Extracción de relaciones lógicas:** representa los conectores reconocidos mediante símbolos lógicos.
- 🌳 **Árbol semántico ramificado:** desarrolla las alternativas correspondientes a cada conector.
- ❌ **Detección de contradicciones:** cierra las ramas que contienen una proposición y su negación.
- ✅ **Identificación de mundos válidos:** muestra las ramas abiertas y sus posibles asignaciones de valores de verdad.
- 📊 **Visualización gráfica:** genera una representación del árbol mediante una estructura jerárquica.
- 💾 **Almacenamiento de datos:** guarda las proposiciones, reglas y premisas en un archivo JSON.
- 🧹 **Limpieza de la base de conocimientos:** permite reiniciar los datos desde la interfaz.

## 🔗 Conectores lógicos implementados

El parser reconoce los siguientes conectores en las formas de escritura indicadas:

| Conector | Símbolo | Ejemplo |
|---|:---:|---|
| Conjunción | `∧` | `Tengo fiebre y tengo tos` |
| Disyunción | `∨` | `Llueve o hace frío` |
| Negación | `¬` | `No tengo fiebre` |
| Implicación | `→` | `Si llueve entonces llevo paraguas` |
| Bicondicional | `↔` | `Tengo fiebre si y solo si tengo temperatura alta` |

> 💡 El bicondicional reconoce las variantes «si y solo si» y «si y sólo si», con o sin una coma inmediatamente anterior al conector.

### 🚦 Interpretación de las ramas

- 🟢 **Rama abierta:** no se ha encontrado una contradicción; representa una interpretación compatible con las fórmulas desarrolladas.
- 🔴 **Rama cerrada:** contiene una contradicción y no puede representar un mundo válido.
- 🌎 **Mundo posible:** asignación de valores de verdad compatible con las premisas y las reglas de la base de conocimientos.

Si todas las ramas se cierran, la base de conocimientos es inconsistente bajo las premisas que se consideran verdaderas.

## 🛠️ Tecnologías utilizadas

| Tecnología | Función |
|---|---|
| 🐍 Python | Lenguaje de programación |
| 🖥️ Tkinter | Interfaz gráfica de escritorio |
| 🕸️ NetworkX | Estructuras de grafos y conexiones entre nodos |
| 📈 Matplotlib | Representación gráfica del árbol semántico |
| 💾 JSON | Persistencia de la base de conocimientos |

## 📦 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU-USUARIO/TU-REPOSITORIO.git
```

Reemplaza `TU-USUARIO` y `TU-REPOSITORIO` por los datos de tu repositorio.

### 2. Entrar al directorio del proyecto

```bash
cd TU-REPOSITORIO
```

### 3. Instalar las dependencias

```bash
python -m pip install networkx matplotlib
```

**Requisito:** se necesita Python 3.10 o posterior. Tkinter normalmente está incluido en las instalaciones de Python para Windows; en algunas distribuciones de Linux es necesario instalarlo por separado.

### 4. Ejecutar la aplicación

Si el archivo principal se llama `arbol_semantico_corregido.py`, ejecuta:

```bash
python arbol_semantico_corregido.py
```

Si tu archivo principal tiene otro nombre, sustituye el nombre del comando.

## 🎮 Uso de la aplicación

1. Abre el programa.
2. Escribe una proposición o regla en el campo de entrada.
3. Pulsa **Procesar** o presiona `Enter`.
4. Revisa el arreglo de proposiciones y el arreglo de relaciones.
5. Introduce las demás premisas que conforman tu base de conocimientos.
6. Pulsa **Graficar Árbol** para visualizar las ramas, contradicciones y resultados.
7. Utiliza **Limpiar Todo** para reiniciar la base de conocimientos antes de realizar otro ejercicio.

## ⚠️ Consideraciones y limitaciones

- El reconocimiento de texto utiliza patrones y separadores definidos en el programa; no es un analizador completo de lenguaje natural.
- Las proposiciones deben escribirse de forma consistente. Por ejemplo, `tengo tos` y `tos` se interpretan como proposiciones distintas.
- Las premisas introducidas se consideran verdaderas al construir el tableau.
- La cantidad de mundos posibles puede crecer exponencialmente con el número de proposiciones atómicas.
- La validez de los resultados depende de que las oraciones sean interpretadas correctamente por el parser.

## 👨‍💻 Autor

**Víctor Flores**

Proyecto académico orientado al estudio de sistemas expertos.

---
