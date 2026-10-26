import tkinter as tk
from tkinter import messagebox, ttk
import networkx as nx
import matplotlib.pyplot as plt
import json
import os
import textwrap
import re


class ParserSistemasExpertos:
    def __init__(self):
        self.proposiciones = []
        self.reglas = []
        self.reglas_dict = {}
        self.premisas = []
        self.archivo_datos = 'base_conocimientos.json'

    def procesar_oracion(self, texto):
        texto = texto.lower().strip().rstrip('.,!?')
        if not texto:
            return None
        return self._parsear(texto)

    def _obtener_o_crear_proposicion(self, texto):
        texto = texto.strip()
        if texto not in self.proposiciones:
            self.proposiciones.append(texto)
        idx = self.proposiciones.index(texto) + 1
        return f'x[{idx}]'

    def _crear_regla(self, izquierda, derecha, operador):
        r_id = f'r[{len(self.reglas) + 1}]'
        relacion = (izquierda, derecha, operador)
        self.reglas.append((r_id, relacion))
        self.reglas_dict[r_id] = relacion
        return r_id

    def _parsear(self, texto):
        texto = texto.strip()

        # ---------------------------------------------------------
        # 1. BICONDICIONAL: "A si y solo si B"
        # Se comprueba ANTES de buscar "y".
        # ---------------------------------------------------------
        patron_bicondicional = re.search(
            r'(?<!\w)si\s+y\s+s[oó]lo\s+si(?!\w)',
            texto,
            flags=re.IGNORECASE
        )

        if patron_bicondicional:
            izq = texto[:patron_bicondicional.start()].strip(
                ' \t,;:'
            )
            der = texto[patron_bicondicional.end():].strip(
                ' \t,;:.!?¿¡'
            )

            if not izq or not der:
                raise ValueError(
                    'El bicondicional está incompleto. Escriba una '
                    'proposición antes y otra después de '
                    '«si y solo si».'
                )

            p_izq = self._parsear(izq)
            p_der = self._parsear(der)

            return self._crear_regla(
                p_izq,
                p_der,
                '↔'
            )

        # ---------------------------------------------------------
        # 2. IMPLICACIÓN: "Si A entonces B"
        # ---------------------------------------------------------
        if texto.startswith('si '):
            cuerpo = texto[3:].strip()
            ant_raw, cons_raw = None, None

            if ' entonces ' in cuerpo:
                ant_raw, cons_raw = cuerpo.split(
                    ' entonces ', 1
                )

            elif ',' in cuerpo:
                ant_raw, cons_raw = cuerpo.split(',', 1)

            else:
                tokens = cuerpo.split()

                indicadores = [
                    'nos', 'yo', 'tu', 'tú', 'el', 'él',
                    'ella', 'ellos', 'ellas', 'usted',
                    'ustedes', 'nosotros', 'se', 'me',
                    'te', 'le', 'les', 'voy', 'vamos',
                    'va', 'van'
                ]

                split_idx = -1

                for i in range(1, len(tokens)):
                    if tokens[i] in indicadores:
                        split_idx = i
                        break

                if split_idx != -1:
                    ant_raw = ' '.join(tokens[:split_idx])
                    cons_raw = ' '.join(tokens[split_idx:])
                else:
                    mitad = len(tokens) // 2
                    ant_raw = ' '.join(tokens[:mitad])
                    cons_raw = ' '.join(tokens[mitad:])

            ant_parsed = self._parsear(ant_raw)
            cons_parsed = self._parsear(cons_raw)

            return self._crear_regla(
                ant_parsed,
                cons_parsed,
                '⇒'
            )

        # ---------------------------------------------------------
        # 3. CONJUNCIÓN: A y B
        # ---------------------------------------------------------
        elif ' y ' in texto:
            izq, der = texto.split(' y ', 1)

            p_izq = self._parsear(izq)
            p_der = self._parsear(der)

            return self._crear_regla(
                p_izq,
                p_der,
                '∧'
            )

        # ---------------------------------------------------------
        # 4. DISYUNCIÓN: A o B
        # ---------------------------------------------------------
        elif ' o ' in texto:
            izq, der = texto.split(' o ', 1)

            p_izq = self._parsear(izq)
            p_der = self._parsear(der)

            return self._crear_regla(
                p_izq,
                p_der,
                '∨'
            )

        # ---------------------------------------------------------
        # 5. NEGACIÓN: no A
        # ---------------------------------------------------------
        elif texto.startswith('no '):
            base = texto[3:].strip()
            p_base = self._parsear(base)

            r_id = f'r[{len(self.reglas) + 1}]'
            relacion = (p_base, '¬')

            self.reglas.append((r_id, relacion))
            self.reglas_dict[r_id] = relacion

            return r_id

        # ---------------------------------------------------------
        # 6. PROPOSICIÓN ATÓMICA
        # ---------------------------------------------------------
        else:
            return self._obtener_o_crear_proposicion(texto)

    def reiniciar(self):
        self.proposiciones.clear()
        self.reglas.clear()
        self.reglas_dict.clear()
        self.premisas.clear()
        self.guardar_datos()

    def guardar_datos(self):
        datos = {
            'proposiciones': self.proposiciones,
            'reglas': self.reglas,
            'reglas_dict': self.reglas_dict,
            'premisas': self.premisas
        }

        try:
            with open(
                self.archivo_datos,
                'w',
                encoding='utf-8'
            ) as f:
                json.dump(
                    datos,
                    f,
                    ensure_ascii=False,
                    indent=4
                )

        except Exception as e:
            print(f'Error al guardar datos: {e}')

    def cargar_datos(self):
        if os.path.exists(self.archivo_datos):
            try:
                with open(
                    self.archivo_datos,
                    'r',
                    encoding='utf-8'
                ) as f:
                    datos = json.load(f)

                    self.proposiciones = datos.get(
                        'proposiciones', []
                    )

                    self.reglas = [
                        (r[0], tuple(r[1]))
                        for r in datos.get('reglas', [])
                    ]

                    self.reglas_dict = {
                        k: tuple(v)
                        for k, v in datos.get(
                            'reglas_dict', {}
                        ).items()
                    }

                    self.premisas = datos.get(
                        'premisas', []
                    )

            except Exception as e:
                print(f'Error al cargar datos: {e}')


class InterfazSistemasExpertos:
    def __init__(self, root):
        self.root = root
        self.root.title(
            'Extractor de Reglas - Sistemas Expertos'
        )
        self.root.geometry('780x600')
        self.root.resizable(True, True)

        self.motor = ParserSistemasExpertos()

        self._crear_componentes()

        self.motor.cargar_datos()
        self.actualizar_vistas()

    def _crear_componentes(self):
        style = ttk.Style()
        style.theme_use('clam')

        main_frame = ttk.Frame(
            self.root,
            padding='15'
        )
        main_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        lbl_titulo = ttk.Label(
            main_frame,
            text='Detector de Proposiciones y Árbol Semántico',
            font=('Helvetica', 14, 'bold')
        )
        lbl_titulo.pack(pady=(0, 10))

        input_frame = ttk.LabelFrame(
            main_frame,
            text=' Introducir Oración / Regla ',
            padding='10'
        )
        input_frame.pack(
            fill=tk.X,
            pady=(0, 10)
        )

        self.txt_oracion = ttk.Entry(
            input_frame,
            font=('Helvetica', 11)
        )
        self.txt_oracion.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(0, 10)
        )
        self.txt_oracion.bind(
            '<Return>',
            lambda event: self.procesar()
        )

        btn_procesar = ttk.Button(
            input_frame,
            text='Procesar',
            command=self.procesar
        )
        btn_procesar.pack(
            side=tk.LEFT,
            padx=(0, 5)
        )

        btn_limpiar = ttk.Button(
            input_frame,
            text='Limpiar Todo',
            command=self.limpiar
        )
        btn_limpiar.pack(
            side=tk.LEFT,
            padx=(0, 5)
        )

        btn_graficar = ttk.Button(
            input_frame,
            text='Graficar Árbol',
            command=self.graficar_arbol
        )
        btn_graficar.pack(side=tk.LEFT)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        prop_frame = ttk.LabelFrame(
            content_frame,
            text=' Arreglo de Proposiciones (x) ',
            padding='10'
        )
        prop_frame.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True,
            padx=(0, 5)
        )

        self.lst_proposiciones = tk.Listbox(
            prop_frame,
            font=('Courier New', 10),
            selectmode=tk.SINGLE
        )
        self.lst_proposiciones.pack(
            fill=tk.BOTH,
            expand=True
        )

        reglas_frame = ttk.LabelFrame(
            content_frame,
            text=' Arreglo de Relaciones / Reglas (r) ',
            padding='10'
        )
        reglas_frame.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
            expand=True,
            padx=(5, 0)
        )

        self.lst_reglas = tk.Listbox(
            reglas_frame,
            font=('Courier New', 10),
            selectmode=tk.SINGLE
        )
        self.lst_reglas.pack(
            fill=tk.BOTH,
            expand=True
        )

        self.lbl_status = ttk.Label(
            main_frame,
            text='Ingrese una regla y presione Procesar o Enter.',
            font=('Helvetica', 9, 'italic')
        )
        self.lbl_status.pack(
            anchor=tk.W,
            pady=(10, 0)
        )

    def procesar(self):
        texto = self.txt_oracion.get().strip()

        if not texto:
            messagebox.showwarning(
                'Entrada vacía',
                'Por favor ingrese una oración o regla.'
            )
            return

        try:
            resultado = self.motor.procesar_oracion(texto)

            if resultado:
                self.motor.premisas.append(resultado)
                self.motor.guardar_datos()
                self.actualizar_vistas()

                self.txt_oracion.delete(0, tk.END)

                self.lbl_status.config(
                    text=(
                        f"Premisa '{resultado}' agregada "
                        'a la Base de Conocimientos.'
                    )
                )

        except ValueError as e:
            messagebox.showerror(
                'Error en la regla',
                str(e)
            )

    def actualizar_vistas(self):
        self.lst_proposiciones.delete(0, tk.END)

        for idx, prop in enumerate(
            self.motor.proposiciones,
            1
        ):
            self.lst_proposiciones.insert(
                tk.END,
                f"x[{idx}] = '{prop}'"
            )

        self.lst_reglas.delete(0, tk.END)

        for r_id, relacion in self.motor.reglas:
            if len(relacion) == 3:
                str_rel = (
                    f'{r_id} = '
                    f'({relacion[0]}, {relacion[1]}, '
                    f'{relacion[2]})'
                )
            else:
                str_rel = (
                    f'{r_id} = '
                    f'({relacion[0]}, {relacion[1]})'
                )

            self.lst_reglas.insert(
                tk.END,
                str_rel
            )

    def limpiar(self):
        self.motor.reiniciar()

        self.lst_proposiciones.delete(0, tk.END)
        self.lst_reglas.delete(0, tk.END)
        self.txt_oracion.delete(0, tk.END)

        self.lbl_status.config(
            text=(
                'Se han limpiado todas las proposiciones, '
                'reglas y premisas.'
            )
        )

    def graficar_arbol(self):
        """
        Construye un tableau semántico ramificado.

        Todas las premisas introducidas se consideran verdaderas.
        Las ramas se cierran si aparece una contradicción.
        Las ramas abiertas representan modelos posibles.
        """

        if not self.motor.premisas:
            messagebox.showwarning(
                'Sin datos',
                'No hay premisas en la base de conocimientos.'
            )
            return

        cantidad_atomos = len(
            self.motor.proposiciones
        )

        completar_mundos = True

        if cantidad_atomos > 6:
            completar_mundos = messagebox.askyesno(
                'Enumeración de mundos posibles',
                f'La base contiene {cantidad_atomos} '
                'proposiciones. Enumerar todos los mundos '
                f'puede generar hasta {2 ** cantidad_atomos:,} '
                'asignaciones y una gráfica muy grande.\n\n'
                '¿Desea enumerar todos los mundos?\n\n'
                'Seleccione «No» para conservar las ramas '
                'abiertas y mostrar las proposiciones libres.'
            )

        G = nx.DiGraph()

        contador_nodos = [0]
        mundos_validos = []
        mundos_por_asignacion = {}
        mundos_repetidos = [0]
        ramas_cerradas = [0]

        def agregar_nodo(padre, etiqueta, color):
            nodo = contador_nodos[0]
            contador_nodos[0] += 1

            G.add_node(
                nodo,
                label=etiqueta,
                color=color
            )

            if padre is not None:
                G.add_edge(padre, nodo)

            return nodo

        def es_atomo(formula):
            return (
                isinstance(formula, str)
                and formula.startswith('x[')
                and formula.endswith(']')
            )

        def texto_formula(formula, visitados=None):
            """
            Convierte identificadores x[n] y r[n]
            en expresiones legibles.
            """
            if visitados is None:
                visitados = set()

            if formula in visitados:
                return str(formula)

            if es_atomo(formula):
                try:
                    indice = int(formula[2:-1]) - 1

                    if (
                        0 <= indice
                        < len(self.motor.proposiciones)
                    ):
                        return self.motor.proposiciones[
                            indice
                        ]

                except (ValueError, TypeError):
                    pass

                return str(formula)

            relacion = self.motor.reglas_dict.get(
                formula
            )

            if relacion is None:
                return str(formula)

            visitados = set(visitados)
            visitados.add(formula)

            if (
                len(relacion) == 2
                and relacion[1] == '¬'
            ):
                return (
                    f'¬({texto_formula(relacion[0], visitados)})'
                )

            if len(relacion) == 3:
                izquierda, derecha, operador = relacion

                simbolos = {
                    '⇒': '→',
                    '∧': '∧',
                    '∨': '∨',
                    '↔': '↔'
                }

                simbolo = simbolos.get(
                    operador,
                    operador
                )

                return (
                    f'({texto_formula(izquierda, visitados)} '
                    f'{simbolo} '
                    f'{texto_formula(derecha, visitados)})'
                )

            return str(formula)

        def envolver(
            texto,
            ancho=27,
            max_lineas=3
        ):
            lineas = textwrap.wrap(
                str(texto),
                width=ancho,
                break_long_words=False,
                break_on_hyphens=False
            )

            if not lineas:
                return ''

            if len(lineas) > max_lineas:
                lineas = lineas[:max_lineas]

                if len(lineas[-1]) > ancho - 1:
                    lineas[-1] = lineas[-1][:ancho - 1]

                lineas[-1] = (
                    lineas[-1].rstrip(' .') + '…'
                )

            return '\n'.join(lineas)

        def texto_mundo(asignaciones):
            lineas = []

            for indice, proposicion in enumerate(
                self.motor.proposiciones,
                start=1
            ):
                atomo = f'x[{indice}]'
                valor = asignaciones.get(
                    atomo,
                    None
                )

                if valor is True:
                    estado = 'V'
                elif valor is False:
                    estado = 'F'
                else:
                    estado = 'libre'

                nombre = envolver(
                    proposicion,
                    ancho=23,
                    max_lineas=1
                )

                lineas.append(
                    f'x[{indice}] {nombre}: {estado}'
                )

            return '\n'.join(lineas) if lineas else (
                '(sin proposiciones atómicas)'
            )

        def cerrar_rama(
            padre,
            atomo,
            valor_previo,
            valor_actual
        ):
            ramas_cerradas[0] += 1

            nombre = texto_formula(atomo)

            antes = 'V' if valor_previo else 'F'
            ahora = 'V' if valor_actual else 'F'

            agregar_nodo(
                padre,
                f'× RAMA CERRADA\n'
                f'Contradicción:\n'
                f'{nombre}\n'
                f'aparece como {antes} y {ahora}',
                '#f4a6a6'
            )

        def finalizar_rama(padre, asignaciones):
            libres = [
                f'x[{i}]'
                for i in range(
                    1,
                    len(self.motor.proposiciones) + 1
                )
                if f'x[{i}]' not in asignaciones
            ]

            if completar_mundos and not libres:
                firma = tuple(
                    asignaciones.get(f'x[{i}]')
                    for i in range(
                        1,
                        cantidad_atomos + 1
                    )
                )

                if firma in mundos_por_asignacion:
                    mundos_repetidos[0] += 1

                    referencia = mundos_por_asignacion[
                        firma
                    ]

                    agregar_nodo(
                        padre,
                        '↪ MUNDO REPETIDO\n'
                        'La misma asignación ya aparece\n'
                        f'como mundo válido #{referencia}',
                        '#e2e8f0'
                    )
                    return

            numero = len(mundos_validos) + 1

            if libres:
                titulo = f'✓ RAMA ABIERTA #{numero}'

                detalle = texto_mundo(
                    asignaciones
                )

                detalle += (
                    '\nLas proposiciones libres '
                    'pueden tomar V o F.'
                )

            else:
                titulo = f'✓ MUNDO VÁLIDO #{numero}'

                detalle = texto_mundo(
                    asignaciones
                )

                firma = tuple(
                    asignaciones.get(f'x[{i}]')
                    for i in range(
                        1,
                        cantidad_atomos + 1
                    )
                )

                if completar_mundos:
                    mundos_por_asignacion[
                        firma
                    ] = numero

            hoja = agregar_nodo(
                padre,
                f'{titulo}\n{detalle}',
                '#b7e4c7'
            )

            mundos_validos.append({
                'nodo': hoja,
                'asignaciones': dict(asignaciones),
                'libres': list(libres)
            })

        def desarrollar(
            padre,
            pendientes,
            asignaciones,
            expandidas,
            profundidad=0
        ):
            """
            Desarrolla una rama utilizando las reglas
            semánticas de cada conector.
            """

            if profundidad > 700:
                agregar_nodo(
                    padre,
                    '⚠ Límite de profundidad alcanzado',
                    '#f6d365'
                )
                return

            # Cuando no quedan fórmulas por expandir,
            # se completan las asignaciones si corresponde.
            if not pendientes:

                if completar_mundos:
                    siguiente = next(
                        (
                            f'x[{i}]'
                            for i in range(
                                1,
                                cantidad_atomos + 1
                            )
                            if f'x[{i}]'
                            not in asignaciones
                        ),
                        None
                    )

                    if siguiente is not None:
                        nombre = texto_formula(
                            siguiente
                        )

                        for valor in (True, False):
                            copia_asignaciones = dict(
                                asignaciones
                            )

                            copia_asignaciones[
                                siguiente
                            ] = valor

                            estado = (
                                'VERDADERO'
                                if valor
                                else 'FALSO'
                            )

                            rama = agregar_nodo(
                                padre,
                                'MUNDO POSIBLE\n'
                                f'{envolver(nombre)} = {estado}',
                                '#ffe2a8'
                            )

                            desarrollar(
                                rama,
                                [],
                                copia_asignaciones,
                                set(expandidas),
                                profundidad + 1
                            )

                        return

                finalizar_rama(
                    padre,
                    asignaciones
                )
                return

            formula, verdad = pendientes[0]
            resto = pendientes[1:]

            formula_legible = texto_formula(
                formula
            )

            signo = 'V' if verdad else 'F'

            nodo_formula = agregar_nodo(
                padre,
                f'{signo}: '
                f'{envolver(formula_legible, ancho=30, max_lineas=4)}',
                '#dceafe'
            )

            # -------------------------------------------------
            # LITERALES: comprobar contradicciones.
            # -------------------------------------------------
            if (
                es_atomo(formula)
                or formula not in self.motor.reglas_dict
            ):
                if (
                    formula in asignaciones
                    and asignaciones[formula] != verdad
                ):
                    cerrar_rama(
                        nodo_formula,
                        formula,
                        asignaciones[formula],
                        verdad
                    )
                    return

                copia_asignaciones = dict(
                    asignaciones
                )

                copia_asignaciones[
                    formula
                ] = verdad

                desarrollar(
                    nodo_formula,
                    resto,
                    copia_asignaciones,
                    set(expandidas),
                    profundidad + 1
                )
                return

            relacion = self.motor.reglas_dict[
                formula
            ]

            clave = (formula, verdad)

            if clave in expandidas:
                desarrollar(
                    nodo_formula,
                    resto,
                    dict(asignaciones),
                    set(expandidas),
                    profundidad + 1
                )
                return

            nuevas_expandidas = set(expandidas)
            nuevas_expandidas.add(clave)

            # -------------------------------------------------
            # NEGACIÓN:
            # V(¬A) -> F(A)
            # F(¬A) -> V(A)
            # -------------------------------------------------
            if (
                len(relacion) == 2
                and relacion[1] == '¬'
            ):
                hijo = relacion[0]

                desarrollar(
                    nodo_formula,
                    [(hijo, not verdad)] + resto,
                    dict(asignaciones),
                    nuevas_expandidas,
                    profundidad + 1
                )
                return

            if len(relacion) != 3:
                agregar_nodo(
                    nodo_formula,
                    '⚠ Fórmula no reconocida',
                    '#f6d365'
                )
                return

            izquierda, derecha, operador = relacion

            def misma_rama(formulas_nuevas):
                desarrollar(
                    nodo_formula,
                    formulas_nuevas + resto,
                    dict(asignaciones),
                    set(nuevas_expandidas),
                    profundidad + 1
                )

            def bifurcar(alternativas):
                for (
                    formula_rama,
                    valor_rama,
                    nombre_rama
                ) in alternativas:

                    desarrollar(
                        nodo_formula,
                        [(formula_rama, valor_rama)] + resto,
                        dict(asignaciones),
                        set(nuevas_expandidas),
                        profundidad + 1
                    )

            # -------------------------------------------------
            # CONJUNCIÓN:
            # V(A∧B): V(A), V(B), misma rama.
            # F(A∧B): F(A) | F(B), dos ramas.
            # -------------------------------------------------
            if operador == '∧':
                if verdad:
                    misma_rama([
                        (izquierda, True),
                        (derecha, True)
                    ])
                else:
                    bifurcar([
                        (
                            izquierda,
                            False,
                            'alternativa izquierda'
                        ),
                        (
                            derecha,
                            False,
                            'alternativa derecha'
                        )
                    ])

            # -------------------------------------------------
            # DISYUNCIÓN:
            # V(A∨B): V(A) | V(B), dos ramas.
            # F(A∨B): F(A), F(B), misma rama.
            # -------------------------------------------------
            elif operador == '∨':
                if verdad:
                    bifurcar([
                        (
                            izquierda,
                            True,
                            'alternativa izquierda'
                        ),
                        (
                            derecha,
                            True,
                            'alternativa derecha'
                        )
                    ])
                else:
                    misma_rama([
                        (izquierda, False),
                        (derecha, False)
                    ])

            # -------------------------------------------------
            # IMPLICACIÓN:
            # V(A→B): F(A) | V(B), dos ramas.
            # F(A→B): V(A), F(B), misma rama.
            # -------------------------------------------------
            elif operador in ('⇒', '→'):
                if verdad:
                    bifurcar([
                        (
                            izquierda,
                            False,
                            'antecedente falso'
                        ),
                        (
                            derecha,
                            True,
                            'consecuente verdadero'
                        )
                    ])
                else:
                    misma_rama([
                        (izquierda, True),
                        (derecha, False)
                    ])

            # -------------------------------------------------
            # BICONDICIONAL:
            #
            # V(A↔B):
            #   Rama 1: V(A), V(B)
            #   Rama 2: F(A), F(B)
            #
            # F(A↔B):
            #   Rama 1: V(A), F(B)
            #   Rama 2: F(A), V(B)
            # -------------------------------------------------
            elif operador == '↔':
                if verdad:
                    alternativas = [
                        [
                            (izquierda, True),
                            (derecha, True)
                        ],
                        [
                            (izquierda, False),
                            (derecha, False)
                        ]
                    ]
                else:
                    alternativas = [
                        [
                            (izquierda, True),
                            (derecha, False)
                        ],
                        [
                            (izquierda, False),
                            (derecha, True)
                        ]
                    ]

                for alternativa in alternativas:
                    desarrollar(
                        nodo_formula,
                        alternativa + resto,
                        dict(asignaciones),
                        set(nuevas_expandidas),
                        profundidad + 1
                    )

            else:
                agregar_nodo(
                    nodo_formula,
                    f'⚠ Conector no soportado: {operador}',
                    '#f6d365'
                )

        # Nodo raíz.
        raiz = agregar_nodo(
            None,
            'ÁRBOL SEMÁNTICO\n'
            'Todas las premisas se consideran verdaderas',
            '#bde0fe'
        )

        # Todas las premisas comienzan en una sola rama.
        pendientes_iniciales = [
            (premisa, True)
            for premisa in self.motor.premisas
        ]

        desarrollar(
            raiz,
            pendientes_iniciales,
            {},
            set()
        )

        # -----------------------------------------------------
        # MOSTRAR EN LA TERMINAL LOS MUNDOS / RAMAS VÁLIDAS.
        # Este bloque solo imprime los resultados calculados;
        # no modifica el árbol, las reglas ni la interfaz.
        # -----------------------------------------------------
        print("\n" + "=" * 76)
        print("MUNDOS VÁLIDOS QUE SATISFACEN LA BASE DE CONOCIMIENTOS")
        print("=" * 76)
        print("Premisas consideradas verdaderas:")
        for indice, premisa in enumerate(self.motor.premisas, start=1):
            print(f"  {indice}. {texto_formula(premisa)}")

        if mundos_validos:
            if completar_mundos:
                print(
                    f"\nTotal de mundos válidos distintos: "
                    f"{len(mundos_validos)}"
                )
                for numero, mundo in enumerate(mundos_validos, start=1):
                    print(f"\n🌎 MUNDO VÁLIDO #{numero}")
                    asignaciones = mundo['asignaciones']

                    for indice, proposicion in enumerate(
                        self.motor.proposiciones,
                        start=1
                    ):
                        atomo = f'x[{indice}]'
                        valor = asignaciones.get(atomo)

                        if valor is True:
                            estado = 'VERDADERO (V)'
                        elif valor is False:
                            estado = 'FALSO (F)'
                        else:
                            estado = 'SIN ASIGNAR'

                        print(
                            f"  {atomo} ({proposicion}) = {estado}"
                        )
            else:
                print(
                    f"\nTotal de ramas abiertas: {len(mundos_validos)}"
                )
                print(
                    "Nota: se muestran las asignaciones de cada rama abierta; "
                    "las proposiciones libres pueden ser V o F."
                )

                for numero, mundo in enumerate(mundos_validos, start=1):
                    print(f"\n🌿 RAMA ABIERTA #{numero}")
                    asignaciones = mundo['asignaciones']

                    for indice, proposicion in enumerate(
                        self.motor.proposiciones,
                        start=1
                    ):
                        atomo = f'x[{indice}]'
                        valor = asignaciones.get(atomo)

                        if valor is True:
                            estado = 'VERDADERO (V)'
                        elif valor is False:
                            estado = 'FALSO (F)'
                        else:
                            estado = 'LIBRE (V o F)'

                        print(
                            f"  {atomo} ({proposicion}) = {estado}"
                        )
        else:
            print("\n❌ No existen mundos válidos: todas las ramas se cerraron.")

        print(f"\nRamas cerradas por contradicción: {ramas_cerradas[0]}")
        if mundos_repetidos[0]:
            print(
                f"Ramas que repetían un mundo ya listado: "
                f"{mundos_repetidos[0]}"
            )
        print("=" * 76 + "\n")

        # -----------------------------------------------------
        # DISTRIBUCIÓN JERÁRQUICA DEL ÁRBOL.
        # -----------------------------------------------------
        posiciones = {}
        siguiente_hoja = [0]
        profundidades = [0]

        def posicionar(nodo, profundidad=0):
            profundidades[0] = max(
                profundidades[0],
                profundidad
            )

            hijos = list(
                G.successors(nodo)
            )

            if not hijos:
                x = siguiente_hoja[0]
                siguiente_hoja[0] += 1

            else:
                xs = [
                    posicionar(
                        hijo,
                        profundidad + 1
                    )
                    for hijo in hijos
                ]

                x = sum(xs) / len(xs)

            posiciones[nodo] = (
                x,
                -profundidad
            )

            return x

        posicionar(raiz)

        cantidad_hojas = max(
            1,
            siguiente_hoja[0]
        )

        ancho_figura = max(
            14,
            min(1.45 * cantidad_hojas, 60)
        )

        alto_figura = max(
            8,
            min(0.85 * (profundidades[0] + 1), 40)
        )

        fig, ax = plt.subplots(
            figsize=(
                ancho_figura,
                alto_figura
            )
        )

        ax.set_title(
            f'Árbol semántico — '
            f'{len(mundos_validos)} mundo(s)/rama(s) válido(s), '
            f'{ramas_cerradas[0]} rama(s) cerrada(s)',
            fontsize=13,
            pad=18
        )

        nx.draw_networkx_edges(
            G,
            posiciones,
            ax=ax,
            arrows=True,
            arrowstyle='-|>',
            arrowsize=12,
            edge_color='#64748b',
            width=1.1,
            min_source_margin=6,
            min_target_margin=8
        )

        for nodo, (x, y) in posiciones.items():
            atributos = G.nodes[nodo]

            color = atributos.get(
                'color',
                '#dceafe'
            )

            etiqueta = atributos.get(
                'label',
                ''
            )

            ax.text(
                x,
                y,
                etiqueta,
                ha='center',
                va='center',
                fontsize=7.5,
                bbox=dict(
                    boxstyle='round,pad=0.38',
                    facecolor=color,
                    edgecolor='#475569',
                    linewidth=0.8,
                    alpha=0.98
                ),
                zorder=3
            )

        ax.margins(
            x=0.04,
            y=0.08
        )

        ax.axis('off')
        fig.tight_layout()
        plt.show()

        # -----------------------------------------------------
        # MENSAJE FINAL.
        # -----------------------------------------------------
        if mundos_validos:
            if completar_mundos:
                mensaje = (
                    f'Árbol terminado: '
                    f'{len(mundos_validos)} mundo(s) válido(s) '
                    f'y {ramas_cerradas[0]} rama(s) cerrada(s); '
                    f'{mundos_repetidos[0]} rama(s) repitieron '
                    'un mundo ya listado.'
                )
            else:
                mensaje = (
                    f'Árbol terminado: '
                    f'{len(mundos_validos)} rama(s) abierta(s) '
                    f'y {ramas_cerradas[0]} rama(s) cerrada(s). '
                    'Las proposiciones marcadas como «libre» '
                    'pueden tomar V o F.'
                )
        else:
            mensaje = (
                'La base de conocimientos es inconsistente: '
                'todas las ramas se cerraron y no existe '
                'ningún mundo válido.'
            )

        self.lbl_status.config(
            text=mensaje
        )


if __name__ == '__main__':
    root = tk.Tk()
    app = InterfazSistemasExpertos(root)
    root.mainloop()
