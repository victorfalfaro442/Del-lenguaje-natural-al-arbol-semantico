import json
import re
import sys
import textwrap

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:  # permite usar el motor y --test sin entorno gráfico
    tk = None

# ---------------------------------------------------------------------------
# Colores de los nodos
# ---------------------------------------------------------------------------
COLOR_RAIZ = '#bde0fe'
COLOR_FORMULA = '#dceafe'
COLOR_CERRADA = '#f4a6a6'
COLOR_OK = '#b7e4c7'
COLOR_REPETIDO = '#e2e8f0'
COLOR_ASIGNA = '#ffe2a8'
COLOR_AVISO = '#f6d365'

SIMBOLOS = {'⇒': '→', '→': '→', '∧': '∧', '∨': '∨', '↔': '↔', '⊕': '⊕'}

# ---------------------------------------------------------------------------
# Patrones del parser
# ---------------------------------------------------------------------------
RE_BICOND = re.compile(r'\bsi\s+y\s+s[oó]lo\s+si\b')
RE_SOLO_SI = re.compile(r'\bs[oó]lo\s+si\b')
RE_ENTONCES = re.compile(r'\s*,?\s*\bentonces\b\s*')
RE_XOR = re.compile(r'^o\s+(?:bien\s+)?(.+?),?\s+o\s+(?:bien\s+)?(.+)$')
RE_NI = re.compile(r'^ni\s+(.+?),?\s+ni\s+(.+)$')
RE_SI_POSTFIJO = re.compile(r',?\s+si\s+')
RE_O = re.compile(r',?\s+o\s+')
RE_Y = re.compile(r'\s+y\s+')

INDICADORES = {
    'nos', 'yo', 'tu', 'tú', 'el', 'él', 'ella', 'ellos', 'ellas',
    'usted', 'ustedes', 'nosotros', 'se', 'me', 'te', 'le', 'les',
    'voy', 'vamos', 'va', 'van'
}

_ACENTOS = str.maketrans('áéíóúü', 'aeiouu')


def _limpiar(texto):
    """Quita espacios repetidos y puntuación en los extremos."""
    return re.sub(r'\s+', ' ', texto).strip(' \t,;:.!?¿¡')


def _clave(texto):
    """Clave de comparación de proposiciones: sin acentos en vocales."""
    return _limpiar(texto.lower()).translate(_ACENTOS)


# ===========================================================================
# PARSER
# ===========================================================================
class ParserSistemasExpertos:
    def __init__(self, archivo_datos='base_conocimientos.json'):
        self.proposiciones = []
        self.reglas = []
        self.reglas_dict = {}
        self.premisas = []
        self.archivo_datos = archivo_datos

    # ----------------------------- API pública -----------------------------
    def procesar_oracion(self, texto):
        texto = _limpiar(texto.lower())
        if not texto:
            return None

        n_prop, n_reg = len(self.proposiciones), len(self.reglas)
        try:
            return self._parsear(texto)
        except ValueError:
            # Revertir cualquier proposición o regla creada a medias.
            del self.proposiciones[n_prop:]
            for r_id, _ in self.reglas[n_reg:]:
                self.reglas_dict.pop(r_id, None)
            del self.reglas[n_reg:]
            raise

    def reiniciar(self):
        self.proposiciones.clear()
        self.reglas.clear()
        self.reglas_dict.clear()
        self.premisas.clear()
        self.guardar_datos()

    # ------------------------------ creación -------------------------------
    def _obtener_o_crear_proposicion(self, texto):
        texto = _limpiar(texto)
        if not texto:
            raise ValueError('Hay una proposición vacía en la oración.')
        clave = _clave(texto)
        for i, existente in enumerate(self.proposiciones):
            if _clave(existente) == clave:
                return f'x[{i + 1}]'
        self.proposiciones.append(texto)
        return f'x[{len(self.proposiciones)}]'

    def _crear_regla(self, izquierda, derecha, operador):
        r_id = f'r[{len(self.reglas) + 1}]'
        relacion = (izquierda, derecha, operador)
        self.reglas.append((r_id, relacion))
        self.reglas_dict[r_id] = relacion
        return r_id

    def _crear_negacion(self, base):
        r_id = f'r[{len(self.reglas) + 1}]'
        relacion = (base, '¬')
        self.reglas.append((r_id, relacion))
        self.reglas_dict[r_id] = relacion
        return r_id

    # ------------------------------- parseo --------------------------------
    def _binaria(self, texto, m, operador, nombre, invertir=False):
        izq = _limpiar(texto[:m.start()])
        der = _limpiar(texto[m.end():])
        if not izq or not der:
            raise ValueError(
                f'Falta una proposición antes o después de «{nombre}».'
            )
        p_izq = self._parsear(izq)
        p_der = self._parsear(der)
        if invertir:
            p_izq, p_der = p_der, p_izq
        return self._crear_regla(p_izq, p_der, operador)

    def _implicacion_prefija(self, cuerpo):
        """'Si <cuerpo>' con 'entonces', coma o pronombre como separador."""
        m = RE_ENTONCES.search(cuerpo)
        if m:
            ant, cons = cuerpo[:m.start()], cuerpo[m.end():]
        elif ',' in cuerpo:
            ant, cons = cuerpo.split(',', 1)
        else:
            tokens = cuerpo.split()
            corte = next(
                (i for i in range(1, len(tokens)) if tokens[i] in INDICADORES),
                None
            )
            if corte is None:
                raise ValueError(
                    'No se puede separar el antecedente del consecuente. '
                    'Use «Si A entonces B» o «Si A, B».'
                )
            ant, cons = ' '.join(tokens[:corte]), ' '.join(tokens[corte:])

        ant, cons = _limpiar(ant), _limpiar(cons)
        if not ant or not cons:
            raise ValueError(
                'La implicación está incompleta: escriba un antecedente '
                'y un consecuente.'
            )
        return self._crear_regla(
            self._parsear(ant), self._parsear(cons), '⇒'
        )

    def _parsear(self, texto):
        """
        Precedencia (de menor a mayor ligadura):
        ↔, solo si, "B si A", "si A entonces B"  <  o  <  y  <  no
        """
        texto = _limpiar(texto)
        if not texto:
            raise ValueError('Hay una parte vacía en la oración.')

        # 1. Bicondicional
        m = RE_BICOND.search(texto)
        if m:
            return self._binaria(texto, m, '↔', 'si y solo si')

        # 2. "A solo si B"  =  A → B
        m = RE_SOLO_SI.search(texto)
        if m:
            return self._binaria(texto, m, '⇒', 'solo si')

        # 3. "Si A entonces B"
        if texto.startswith('si '):
            return self._implicacion_prefija(texto[3:])

        # 4. "B si A"  =  A → B
        m = RE_SI_POSTFIJO.search(texto)
        if m:
            return self._binaria(texto, m, '⇒', 'si', invertir=True)

        # 5. "o bien A o bien B" (disyunción exclusiva)
        m = RE_XOR.match(texto)
        if m:
            return self._crear_regla(
                self._parsear(m.group(1)), self._parsear(m.group(2)), '⊕'
            )

        # 6. "ni A ni B"  =  ¬A ∧ ¬B
        m = RE_NI.match(texto)
        if m:
            na = self._crear_negacion(self._parsear(m.group(1)))
            nb = self._crear_negacion(self._parsear(m.group(2)))
            return self._crear_regla(na, nb, '∧')

        # 7. Disyunción (antes que la conjunción: ∨ liga menos que ∧)
        m = RE_O.search(texto)
        if m:
            return self._binaria(texto, m, '∨', 'o')

        # 8. Conjunción
        m = RE_Y.search(texto)
        if m:
            return self._binaria(texto, m, '∧', 'y')

        # 9. Negación
        if texto.startswith('no '):
            return self._crear_negacion(self._parsear(texto[3:]))

        # 10. Proposición atómica
        return self._obtener_o_crear_proposicion(texto)

    # ------------------------- utilidades de fórmulas ----------------------
    @staticmethod
    def es_atomo(formula):
        return (
            isinstance(formula, str)
            and formula.startswith('x[')
            and formula.endswith(']')
        )

    def texto_formula(self, formula, visitados=frozenset()):
        """Convierte identificadores x[n] / r[n] en texto legible."""
        if formula in visitados:
            return str(formula)

        if self.es_atomo(formula):
            try:
                indice = int(formula[2:-1]) - 1
                if 0 <= indice < len(self.proposiciones):
                    return self.proposiciones[indice]
            except ValueError:
                pass
            return str(formula)

        relacion = self.reglas_dict.get(formula)
        if relacion is None:
            return str(formula)

        visitados = visitados | {formula}
        if len(relacion) == 2 and relacion[1] == '¬':
            return f'¬({self.texto_formula(relacion[0], visitados)})'
        if len(relacion) == 3:
            izq, der, op = relacion
            return (
                f'({self.texto_formula(izq, visitados)} '
                f'{SIMBOLOS.get(op, op)} '
                f'{self.texto_formula(der, visitados)})'
            )
        return str(formula)

    def evaluar(self, formula, valores):
        """Evalúa una fórmula con una asignación {'x[1]': bool, ...}."""
        relacion = self.reglas_dict.get(formula)
        if relacion is None:
            return valores[formula]
        if len(relacion) == 2:
            return not self.evaluar(relacion[0], valores)
        a = self.evaluar(relacion[0], valores)
        b = self.evaluar(relacion[1], valores)
        op = relacion[2]
        if op == '∧':
            return a and b
        if op == '∨':
            return a or b
        if op in ('⇒', '→'):
            return (not a) or b
        if op == '↔':
            return a == b
        if op == '⊕':
            return a != b
        raise ValueError(f'Conector no soportado: {op}')

    # ----------------------------- persistencia ----------------------------
    def guardar_datos(self):
        if not self.archivo_datos:
            return
        datos = {
            'proposiciones': self.proposiciones,
            'reglas': self.reglas,
            'reglas_dict': self.reglas_dict,
            'premisas': self.premisas
        }
        try:
            with open(self.archivo_datos, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
        except OSError as e:
            print(f'Error al guardar datos: {e}')

    def cargar_datos(self):
        import os
        if not self.archivo_datos or not os.path.exists(self.archivo_datos):
            return
        try:
            with open(self.archivo_datos, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            proposiciones = list(datos.get('proposiciones', []))
            reglas = [(r[0], tuple(r[1])) for r in datos.get('reglas', [])]
            reglas_dict = {
                k: tuple(v) for k, v in datos.get('reglas_dict', {}).items()
            }
            premisas = list(datos.get('premisas', []))
        except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
            print(f'Error al cargar datos: {e}')
            return
        # Solo se asigna si todo se leyó bien (nada queda a medias).
        self.proposiciones = proposiciones
        self.reglas = reglas
        self.reglas_dict = reglas_dict
        self.premisas = premisas


# ===========================================================================
# MOTOR DEL TABLERO (sin interfaz)
# ===========================================================================
class Arbol:
    """Árbol simple: listas paralelas de etiquetas, colores e hijos."""

    def __init__(self):
        self.etiquetas = []
        self.colores = []
        self.hijos = []

    def agregar(self, padre, etiqueta, color):
        nodo = len(self.etiquetas)
        self.etiquetas.append(etiqueta)
        self.colores.append(color)
        self.hijos.append([])
        if padre is not None:
            self.hijos[padre].append(nodo)
        return nodo


class Resultado:
    def __init__(self):
        self.arbol = Arbol()
        self.raiz = None
        self.mundos = []          # dicts: nodo, asignaciones, libres
        self.ramas_cerradas = 0
        self.repetidos = 0
        self.advertencias = []


def envolver(texto, ancho=27, max_lineas=3):
    lineas = textwrap.wrap(
        str(texto), width=ancho,
        break_long_words=False, break_on_hyphens=False
    )
    if not lineas:
        return ''
    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        if len(lineas[-1]) > ancho - 1:
            lineas[-1] = lineas[-1][:ancho - 1]
        lineas[-1] = lineas[-1].rstrip(' .') + '…'
    return '\n'.join(lineas)


def texto_mundo(motor, asignaciones):
    lineas = []
    for i, prop in enumerate(motor.proposiciones, start=1):
        valor = asignaciones.get(f'x[{i}]')
        estado = 'V' if valor is True else 'F' if valor is False else 'libre'
        nombre = envolver(prop, ancho=23, max_lineas=1)
        lineas.append(f'x[{i}] {nombre}: {estado}')
    return '\n'.join(lineas) if lineas else '(sin proposiciones atómicas)'


def _alternativas(operador, verdad, a, b):
    """Reglas del tablero: lista de ramas, cada una es una lista de (f, v)."""
    if operador == '∧':
        return [[(a, True), (b, True)]] if verdad else [[(a, False)], [(b, False)]]
    if operador == '∨':
        return [[(a, True)], [(b, True)]] if verdad else [[(a, False), (b, False)]]
    if operador in ('⇒', '→'):
        return [[(a, False)], [(b, True)]] if verdad else [[(a, True), (b, False)]]
    if operador == '↔':
        if verdad:
            return [[(a, True), (b, True)], [(a, False), (b, False)]]
        return [[(a, True), (b, False)], [(a, False), (b, True)]]
    if operador == '⊕':
        if verdad:
            return [[(a, True), (b, False)], [(a, False), (b, True)]]
        return [[(a, True), (b, True)], [(a, False), (b, False)]]
    return None


def resolver(motor, completar_mundos=True):
    """
    Construye el tablero semántico (iterativo, DFS de izquierda a derecha).
    Todas las premisas se consideran verdaderas.
    """
    atomos = [f'x[{i}]' for i in range(1, len(motor.proposiciones) + 1)]
    res = Resultado()
    arbol = res.arbol
    res.raiz = arbol.agregar(
        None,
        'ÁRBOL SEMÁNTICO\nTodas las premisas se consideran verdaderas',
        COLOR_RAIZ
    )
    vistos = {}

    pila = [(
        res.raiz,
        [(p, True) for p in motor.premisas],
        {},
        frozenset()
    )]

    while pila:
        padre, pendientes, asign, expand = pila.pop()

        # ---------------- Rama sin fórmulas pendientes ----------------
        if not pendientes:
            siguiente = None
            if completar_mundos:
                siguiente = next((a for a in atomos if a not in asign), None)

            if siguiente is not None:
                nombre = motor.texto_formula(siguiente)
                alts = []
                for valor in (True, False):
                    nueva = dict(asign)
                    nueva[siguiente] = valor
                    estado = 'VERDADERO' if valor else 'FALSO'
                    nodo = arbol.agregar(
                        padre,
                        f'MUNDO POSIBLE\n{envolver(nombre)} = {estado}',
                        COLOR_ASIGNA
                    )
                    alts.append((nodo, [], nueva, expand))
                pila.extend(reversed(alts))
                continue

            libres = [a for a in atomos if a not in asign]
            firma = None
            if not libres:
                firma = tuple(asign[a] for a in atomos)
                if firma in vistos:
                    res.repetidos += 1
                    arbol.agregar(
                        padre,
                        '↪ MUNDO REPETIDO\n'
                        'La misma asignación ya aparece\n'
                        f'como mundo válido #{vistos[firma]}',
                        COLOR_REPETIDO
                    )
                    continue

            numero = len(res.mundos) + 1
            detalle = texto_mundo(motor, asign)
            if libres:
                titulo = f'✓ RAMA ABIERTA #{numero}'
                detalle += '\nLas proposiciones libres pueden tomar V o F.'
            else:
                titulo = f'✓ MUNDO VÁLIDO #{numero}'
                vistos[firma] = numero

            hoja = arbol.agregar(padre, f'{titulo}\n{detalle}', COLOR_OK)
            res.mundos.append({
                'nodo': hoja,
                'asignaciones': dict(asign),
                'libres': libres
            })
            continue

        # ---------------- Siguiente fórmula pendiente ------------------
        formula, verdad = pendientes[0]
        resto = pendientes[1:]
        signo = 'V' if verdad else 'F'
        nodo_formula = arbol.agregar(
            padre,
            f'{signo}: {envolver(motor.texto_formula(formula), 30, 4)}',
            COLOR_FORMULA
        )

        # Literal: comprobar contradicción.
        if motor.es_atomo(formula) or formula not in motor.reglas_dict:
            if formula in asign and asign[formula] != verdad:
                res.ramas_cerradas += 1
                antes = 'V' if asign[formula] else 'F'
                ahora = 'V' if verdad else 'F'
                arbol.agregar(
                    nodo_formula,
                    '× RAMA CERRADA\nContradicción:\n'
                    f'{motor.texto_formula(formula)}\n'
                    f'aparece como {antes} y {ahora}',
                    COLOR_CERRADA
                )
                continue
            nueva = dict(asign)
            nueva[formula] = verdad
            pila.append((nodo_formula, resto, nueva, expand))
            continue

        relacion = motor.reglas_dict[formula]
        clave = (formula, verdad)
        if clave in expand:  # ya desarrollada en esta rama
            pila.append((nodo_formula, resto, dict(asign), expand))
            continue
        nuevas = expand | {clave}

        # Negación
        if len(relacion) == 2 and relacion[1] == '¬':
            pila.append((
                nodo_formula,
                [(relacion[0], not verdad)] + resto,
                dict(asign),
                nuevas
            ))
            continue

        if len(relacion) != 3:
            res.advertencias.append(f'Fórmula no reconocida: {formula}')
            arbol.agregar(nodo_formula, '⚠ Fórmula no reconocida', COLOR_AVISO)
            continue

        izq, der, op = relacion
        alts = _alternativas(op, verdad, izq, der)
        if alts is None:
            res.advertencias.append(f'Conector no soportado: {op}')
            arbol.agregar(
                nodo_formula, f'⚠ Conector no soportado: {op}', COLOR_AVISO
            )
            continue

        # Se apilan al revés para explorar la rama izquierda primero.
        for alt in reversed(alts):
            pila.append((nodo_formula, alt + resto, dict(asign), nuevas))

    return res


def deducciones(motor, res):
    """
    Con mundos completos: átomos con el mismo valor en todos los mundos.
    Devuelve (siempre_V, siempre_F, contingentes) como listas de texto.
    """
    atomos = [f'x[{i}]' for i in range(1, len(motor.proposiciones) + 1)]
    siempre_v, siempre_f, contingentes = [], [], []
    for a in atomos:
        valores = {m['asignaciones'].get(a) for m in res.mundos}
        nombre = motor.texto_formula(a)
        if valores == {True}:
            siempre_v.append(nombre)
        elif valores == {False}:
            siempre_f.append(nombre)
        else:
            contingentes.append(nombre)
    return siempre_v, siempre_f, contingentes


def imprimir_reporte(motor, res, completar):
    print('\n' + '=' * 76)
    print('MUNDOS VÁLIDOS QUE SATISFACEN LA BASE DE CONOCIMIENTOS')
    print('=' * 76)
    print('Premisas consideradas verdaderas:')
    for i, premisa in enumerate(motor.premisas, start=1):
        print(f'  {i}. {motor.texto_formula(premisa)}')

    if res.mundos:
        if completar:
            print(f'\nTotal de mundos válidos distintos: {len(res.mundos)}')
        else:
            print(f'\nTotal de ramas abiertas: {len(res.mundos)}')
            print('Nota: las proposiciones libres pueden ser V o F.')

        for n, mundo in enumerate(res.mundos, start=1):
            print(f"\n{'🌎 MUNDO VÁLIDO' if completar else '🌿 RAMA ABIERTA'} #{n}")
            for i, prop in enumerate(motor.proposiciones, start=1):
                valor = mundo['asignaciones'].get(f'x[{i}]')
                if valor is True:
                    estado = 'VERDADERO (V)'
                elif valor is False:
                    estado = 'FALSO (F)'
                else:
                    estado = 'LIBRE (V o F)'
                print(f'  x[{i}] ({prop}) = {estado}')

        if completar:
            v, f, c = deducciones(motor, res)
            print('\nQué se deduce de las premisas:')
            print('  Verdadero en todos los mundos : ' + (', '.join(v) or '—'))
            print('  Falso en todos los mundos     : ' + (', '.join(f) or '—'))
            print('  Contingente (depende del mundo): ' + (', '.join(c) or '—'))
    else:
        print('\n❌ No existen mundos válidos: todas las ramas se cerraron.')

    print(f'\nRamas cerradas por contradicción: {res.ramas_cerradas}')
    if res.repetidos:
        print(f'Ramas que repetían un mundo ya listado: {res.repetidos}')
    for aviso in res.advertencias:
        print(f'⚠ {aviso}')
    print('=' * 76 + '\n')


def mensaje_final(res, completar):
    if not res.mundos:
        return (
            'La base de conocimientos es inconsistente: todas las ramas se '
            'cerraron y no existe ningún mundo válido.'
        )
    if completar:
        return (
            f'Árbol terminado: {len(res.mundos)} mundo(s) válido(s) y '
            f'{res.ramas_cerradas} rama(s) cerrada(s); '
            f'{res.repetidos} rama(s) repitieron un mundo ya listado.'
        )
    return (
        f'Árbol terminado: {len(res.mundos)} rama(s) abierta(s) y '
        f'{res.ramas_cerradas} rama(s) cerrada(s). '
        'Las proposiciones marcadas como «libre» pueden tomar V o F.'
    )


def calcular_posiciones(arbol, raiz):
    """Distribución jerárquica (iterativa, sin recursión)."""
    pos = {}
    siguiente_hoja = 0
    max_prof = 0
    pila = [(raiz, 0, False)]
    while pila:
        nodo, prof, listo = pila.pop()
        hijos = arbol.hijos[nodo]
        if hijos and not listo:
            pila.append((nodo, prof, True))
            for h in reversed(hijos):
                pila.append((h, prof + 1, False))
            continue
        if hijos:
            x = sum(pos[h][0] for h in hijos) / len(hijos)
        else:
            x = siguiente_hoja
            siguiente_hoja += 1
        pos[nodo] = (x, -prof)
        max_prof = max(max_prof, prof)
    return pos, siguiente_hoja, max_prof


# ===========================================================================
# INTERFAZ
# ===========================================================================
class InterfazSistemasExpertos:
    def __init__(self, root):
        self.root = root
        self.root.title('Extractor de Reglas - Sistemas Expertos')
        self.root.geometry('780x600')
        self.root.resizable(True, True)

        self.motor = ParserSistemasExpertos()
        self._crear_componentes()
        self.motor.cargar_datos()
        self.actualizar_vistas()

    def _crear_componentes(self):
        ttk.Style().theme_use('clam')

        main_frame = ttk.Frame(self.root, padding='15')
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text='Detector de Proposiciones y Árbol Semántico',
            font=('Helvetica', 14, 'bold')
        ).pack(pady=(0, 10))

        input_frame = ttk.LabelFrame(
            main_frame, text=' Introducir Oración / Regla ', padding='10'
        )
        input_frame.pack(fill=tk.X, pady=(0, 10))

        self.txt_oracion = ttk.Entry(input_frame, font=('Helvetica', 11))
        self.txt_oracion.pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10)
        )
        self.txt_oracion.bind('<Return>', lambda e: self.procesar())

        ttk.Button(
            input_frame, text='Procesar', command=self.procesar
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            input_frame, text='Limpiar Todo', command=self.limpiar
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            input_frame, text='Graficar Árbol', command=self.graficar_arbol
        ).pack(side=tk.LEFT)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        prop_frame = ttk.LabelFrame(
            content_frame, text=' Arreglo de Proposiciones (x) ', padding='10'
        )
        prop_frame.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5)
        )
        self.lst_proposiciones = tk.Listbox(
            prop_frame, font=('Courier New', 10), selectmode=tk.SINGLE
        )
        self.lst_proposiciones.pack(fill=tk.BOTH, expand=True)

        reglas_frame = ttk.LabelFrame(
            content_frame,
            text=' Arreglo de Relaciones / Reglas (r) ',
            padding='10'
        )
        reglas_frame.pack(
            side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0)
        )
        self.lst_reglas = tk.Listbox(
            reglas_frame, font=('Courier New', 10), selectmode=tk.SINGLE
        )
        self.lst_reglas.pack(fill=tk.BOTH, expand=True)

        self.lbl_status = ttk.Label(
            main_frame,
            text='Ingrese una regla y presione Procesar o Enter.',
            font=('Helvetica', 9, 'italic')
        )
        self.lbl_status.pack(anchor=tk.W, pady=(10, 0))

    def procesar(self):
        texto = self.txt_oracion.get().strip()
        if not texto:
            messagebox.showwarning(
                'Entrada vacía', 'Por favor ingrese una oración o regla.'
            )
            return
        try:
            resultado = self.motor.procesar_oracion(texto)
        except ValueError as e:
            messagebox.showerror('Error en la regla', str(e))
            return

        if resultado:
            self.motor.premisas.append(resultado)
            self.motor.guardar_datos()
            self.actualizar_vistas()
            self.txt_oracion.delete(0, tk.END)
            self.lbl_status.config(
                text=f"Premisa '{resultado}' agregada a la Base de Conocimientos."
            )

    def actualizar_vistas(self):
        self.lst_proposiciones.delete(0, tk.END)
        for i, prop in enumerate(self.motor.proposiciones, 1):
            self.lst_proposiciones.insert(tk.END, f"x[{i}] = '{prop}'")

        self.lst_reglas.delete(0, tk.END)
        for r_id, rel in self.motor.reglas:
            if len(rel) == 3:
                s = f'{r_id} = ({rel[0]}, {rel[1]}, {rel[2]})'
            else:
                s = f'{r_id} = ({rel[0]}, {rel[1]})'
            self.lst_reglas.insert(tk.END, s)

    def limpiar(self):
        self.motor.reiniciar()
        self.lst_proposiciones.delete(0, tk.END)
        self.lst_reglas.delete(0, tk.END)
        self.txt_oracion.delete(0, tk.END)
        self.lbl_status.config(
            text='Se han limpiado todas las proposiciones, reglas y premisas.'
        )

    def graficar_arbol(self):
        if not self.motor.premisas:
            messagebox.showwarning(
                'Sin datos', 'No hay premisas en la base de conocimientos.'
            )
            return

        n_atomos = len(self.motor.proposiciones)
        completar = True
        if n_atomos > 6:
            completar = messagebox.askyesno(
                'Enumeración de mundos posibles',
                f'La base contiene {n_atomos} proposiciones. Enumerar todos '
                f'los mundos puede generar hasta {2 ** n_atomos:,} '
                'asignaciones y una gráfica muy grande.\n\n'
                '¿Desea enumerar todos los mundos?\n\n'
                'Seleccione «No» para conservar las ramas abiertas y '
                'mostrar las proposiciones libres.'
            )

        res = resolver(self.motor, completar)
        imprimir_reporte(self.motor, res, completar)
        self._dibujar(res)
        self.lbl_status.config(text=mensaje_final(res, completar))

    def _dibujar(self, res):
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyArrowPatch

        arbol = res.arbol
        posiciones, n_hojas, max_prof = calcular_posiciones(arbol, res.raiz)

        fig, ax = plt.subplots(figsize=(
            max(14, min(1.45 * max(1, n_hojas), 60)),
            max(8, min(0.85 * (max_prof + 1), 40))
        ))
        ax.set_title(
            f'Árbol semántico — {len(res.mundos)} mundo(s)/rama(s) válido(s), '
            f'{res.ramas_cerradas} rama(s) cerrada(s)',
            fontsize=13, pad=18
        )

        # Interacción: arrastrar nodo, arrastrar fondo (pan), rueda (zoom),
        # clic = seleccionar, Esc = quitar selección, R = restaurar.
        posiciones_iniciales = dict(posiciones)
        node_texts = {}
        edge_patches = {}
        seleccionado = {'nodo': None}
        arrastre = {
            'modo': None, 'nodo': None, 'offset': (0.0, 0.0),
            'inicio_pixel': None, 'limites': None
        }

        for origen, hijos in enumerate(arbol.hijos):
            for destino in hijos:
                flecha = FancyArrowPatch(
                    posiciones[origen], posiciones[destino],
                    arrowstyle='-|>', mutation_scale=12, color='#64748b',
                    linewidth=1.1, shrinkA=22, shrinkB=22, zorder=1
                )
                ax.add_patch(flecha)
                edge_patches[(origen, destino)] = flecha

        for nodo, (x, y) in posiciones.items():
            node_texts[nodo] = ax.text(
                x, y, arbol.etiquetas[nodo],
                ha='center', va='center', fontsize=7.5,
                bbox=dict(
                    boxstyle='round,pad=0.38', facecolor=arbol.colores[nodo],
                    edgecolor='#475569', linewidth=0.8, alpha=0.98
                ),
                zorder=3, picker=True
            )

        xs = [p[0] for p in posiciones.values()]
        ys = [p[1] for p in posiciones.values()]
        mx = max(1.2, (max(xs) - min(xs)) * 0.04)
        my = max(1.2, (max(ys) - min(ys)) * 0.04)
        limites_iniciales = (
            (min(xs) - mx, max(xs) + mx), (min(ys) - my, max(ys) + my)
        )
        ax.set_xlim(*limites_iniciales[0])
        ax.set_ylim(*limites_iniciales[1])
        ax.axis('off')

        fig.text(
            0.01, 0.012,
            'Uso: arrastra un nodo para moverlo · arrastra el fondo para '
            'desplazarte · rueda para zoom · Esc quita selección · R restaura',
            ha='left', va='bottom', fontsize=9, color='#334155'
        )
        texto_estado = fig.text(
            0.99, 0.012, 'Ningún nodo seleccionado',
            ha='right', va='bottom', fontsize=9, color='#1d4ed8'
        )
        fig.tight_layout(rect=(0, 0.035, 1, 1))

        def actualizar_flechas():
            for (o, d), flecha in edge_patches.items():
                flecha.set_positions(posiciones[o], posiciones[d])

        def seleccionar(nodo):
            anterior = seleccionado['nodo']
            if anterior in node_texts:
                p = node_texts[anterior].get_bbox_patch()
                p.set_edgecolor('#475569')
                p.set_linewidth(0.8)
            seleccionado['nodo'] = nodo
            if nodo is None:
                texto_estado.set_text('Ningún nodo seleccionado')
            else:
                p = node_texts[nodo].get_bbox_patch()
                p.set_edgecolor('#2563eb')
                p.set_linewidth(2.5)
                resumen = ' — '.join(arbol.etiquetas[nodo].splitlines()[:2])
                texto_estado.set_text(f'Nodo {nodo} seleccionado: {resumen}')
            fig.canvas.draw_idle()

        def nodo_bajo_cursor(event):
            for nodo in reversed(list(node_texts)):
                try:
                    dentro, _ = node_texts[nodo].contains(event)
                except Exception:
                    dentro = False
                if dentro:
                    return nodo
            return None

        def al_presionar(event):
            if event.inaxes != ax or event.button != 1:
                return
            nodo = nodo_bajo_cursor(event)
            if nodo is not None and event.xdata is not None:
                seleccionar(nodo)
                arrastre['modo'] = 'nodo'
                arrastre['nodo'] = nodo
                arrastre['offset'] = (
                    posiciones[nodo][0] - event.xdata,
                    posiciones[nodo][1] - event.ydata
                )
            else:
                seleccionar(None)
                arrastre['modo'] = 'fondo'
                arrastre['inicio_pixel'] = (event.x, event.y)
                arrastre['limites'] = (ax.get_xlim(), ax.get_ylim())

        def al_mover(event):
            modo = arrastre['modo']
            if modo is None or event.x is None or event.y is None:
                return
            if modo == 'nodo':
                nodo = arrastre['nodo']
                x, y = ax.transData.inverted().transform((event.x, event.y))
                ox, oy = arrastre['offset']
                posiciones[nodo] = (x + ox, y + oy)
                node_texts[nodo].set_position(posiciones[nodo])
                actualizar_flechas()
                fig.canvas.draw_idle()
            elif arrastre['inicio_pixel'] is not None:
                ix, iy = arrastre['inicio_pixel']
                (x0, x1), (y0, y1) = arrastre['limites']
                caja = ax.get_window_extent()
                if caja.width <= 0 or caja.height <= 0:
                    return
                dx = -(event.x - ix) * (x1 - x0) / caja.width
                dy = -(event.y - iy) * (y1 - y0) / caja.height
                ax.set_xlim(x0 + dx, x1 + dx)
                ax.set_ylim(y0 + dy, y1 + dy)
                fig.canvas.draw_idle()

        def al_soltar(event):
            arrastre.update(
                modo=None, nodo=None, inicio_pixel=None, limites=None
            )

        def al_scroll(event):
            if event.inaxes != ax or event.xdata is None:
                return
            factor = 1 / 1.2 if event.button == 'up' else 1.2
            xl, yl = ax.get_xlim(), ax.get_ylim()
            xc, yc = event.xdata, event.ydata
            ax.set_xlim(xc - (xc - xl[0]) * factor, xc + (xl[1] - xc) * factor)
            ax.set_ylim(yc - (yc - yl[0]) * factor, yc + (yl[1] - yc) * factor)
            fig.canvas.draw_idle()

        def al_tecla(event):
            if event.key == 'escape':
                seleccionar(None)
            elif event.key and event.key.lower() == 'r':
                posiciones.clear()
                posiciones.update(posiciones_iniciales)
                for nodo, pos in posiciones_iniciales.items():
                    node_texts[nodo].set_position(pos)
                actualizar_flechas()
                ax.set_xlim(*limites_iniciales[0])
                ax.set_ylim(*limites_iniciales[1])
                seleccionar(None)

        fig.canvas.mpl_connect('button_press_event', al_presionar)
        fig.canvas.mpl_connect('motion_notify_event', al_mover)
        fig.canvas.mpl_connect('button_release_event', al_soltar)
        fig.canvas.mpl_connect('scroll_event', al_scroll)
        fig.canvas.mpl_connect('key_press_event', al_tecla)
        plt.show()


# ===========================================================================
# AUTOPRUEBAS (python extractor_reglas_mejorado.py --test)
# ===========================================================================
def autotest():
    import random
    from itertools import product

    fallos = []

    def chequear(condicion, nombre):
        print(f"  [{'OK' if condicion else 'FALLA'}] {nombre}")
        if not condicion:
            fallos.append(nombre)

    def modelos_tableau(motor):
        res = resolver(motor, True)
        n = len(motor.proposiciones)
        lista = [
            tuple(m['asignaciones'][f'x[{i}]'] for i in range(1, n + 1))
            for m in res.mundos
        ]
        return lista

    def modelos_fuerza_bruta(motor):
        n = len(motor.proposiciones)
        salida = set()
        for vals in product((True, False), repeat=n):
            v = {f'x[{i + 1}]': vals[i] for i in range(n)}
            if all(motor.evaluar(p, v) for p in motor.premisas):
                salida.add(vals)
        return salida

    def cargar(oraciones):
        m = ParserSistemasExpertos(archivo_datos=None)
        for o in oraciones:
            m.premisas.append(m.procesar_oracion(o))
        return m

    def equivale(oraciones, funcion):
        """Compara el tablero con una función Python sobre los átomos."""
        m = cargar(oraciones)
        n = len(m.proposiciones)
        esperado = {
            vals for vals in product((True, False), repeat=n) if funcion(*vals)
        }
        obtenido = modelos_tableau(m)
        return set(obtenido) == esperado and len(obtenido) == len(set(obtenido))

    print('\n1. Caso del enunciado (orden de los mundos igual al original)')
    m = cargar([
        'Si es de noche entonces no es de día',
        'Si es de noche entonces salen las brujas',
        'Salen las brujas o salen los duendes',
        'Salen los duendes',
        'Si es de día entonces no es de noche',
    ])
    esperado = [
        (False, False, True, True), (False, True, True, True),
        (False, False, False, True), (False, True, False, True),
        (True, False, True, True),
    ]
    chequear(modelos_tableau(m) == esperado, '5 mundos en el orden esperado')
    chequear(set(modelos_tableau(m)) == modelos_fuerza_bruta(m),
             'coincide con la tabla de verdad')

    print('\n2. Parser')
    chequear(equivale(['llueve o truena y graniza'],
                      lambda a, b, c: a or (b and c)),
             'precedencia: A o B y C = A ∨ (B ∧ C)')
    chequear(equivale(['no llueve o truena'], lambda a, b: (not a) or b),
             'precedencia: "no A o B" = (¬A) ∨ B')
    chequear(equivale(['si llueve y truena entonces graniza o nieva'],
                      lambda a, b, c, d: (not (a and b)) or (c or d)),
             'implicación con conjunción y disyunción')
    chequear(equivale(['llueve si y solo si truena'], lambda a, b: a == b),
             'bicondicional')
    chequear(equivale(['salgo solo si llueve'], lambda s, l: (not s) or l),
             '"A solo si B" = A → B')
    chequear(equivale(['salgo si llueve'], lambda s, l: (not l) or s),
             '"B si A" = A → B')
    chequear(equivale(['o bien llueve o bien graniza'], lambda a, b: a != b),
             '"o bien A o bien B" = A ⊕ B')
    chequear(equivale(['ni llueve ni graniza'],
                      lambda a, b: (not a) and (not b)),
             '"ni A ni B" = ¬A ∧ ¬B')
    chequear(equivale(['Si llueve, entonces graniza.'],
                      lambda a, b: (not a) or b),
             'coma antes de "entonces" y punto final')

    m = cargar(['Salen las brujas, o salen los duendes.'])
    chequear(m.proposiciones == ['salen las brujas', 'salen los duendes'],
             'puntuación interna no genera átomos distintos')

    m = cargar(['Es de día', 'No es de dia'])
    chequear(len(m.proposiciones) == 1, '"día" y "dia" son la misma proposición')

    m = ParserSistemasExpertos(archivo_datos=None)
    error = False
    try:
        m.procesar_oracion('Si llueve entonces')
    except ValueError:
        error = True
    chequear(error and not m.proposiciones and not m.reglas,
             'oración incompleta: error y sin estado parcial')

    m = ParserSistemasExpertos(archivo_datos=None)
    error = False
    try:
        m.procesar_oracion('Si llueve mucho')
    except ValueError:
        error = True
    chequear(error, 'sin "entonces", coma ni pronombre: error (no adivina)')

    print('\n3. Casos límite del motor')
    m = cargar(['llueve', 'no llueve'])
    res = resolver(m, True)
    chequear(not res.mundos and res.ramas_cerradas == 1,
             'premisas contradictorias: 0 mundos, 1 rama cerrada')
    m = cargar(['llueve o no llueve'])
    chequear(len(modelos_tableau(m)) == 2, 'tautología: 2 mundos')

    print('\n4. Motor vs. tabla de verdad (fórmulas aleatorias)')
    random.seed(12345)
    OPS = ['∧', '∨', '⇒', '↔', '⊕']

    def formula_aleatoria(mot, atomos, prof):
        if prof == 0 or random.random() < 0.25:
            return random.choice(atomos)
        if random.random() < 0.2:
            return mot._crear_negacion(
                formula_aleatoria(mot, atomos, prof - 1)
            )
        return mot._crear_regla(
            formula_aleatoria(mot, atomos, prof - 1),
            formula_aleatoria(mot, atomos, prof - 1),
            random.choice(OPS)
        )

    malos = 0
    for _ in range(600):
        mot = ParserSistemasExpertos(archivo_datos=None)
        n = random.randint(1, 5)
        mot.proposiciones = [f'p{i}' for i in range(n)]
        atomos = [f'x[{i + 1}]' for i in range(n)]
        mot.premisas = [
            formula_aleatoria(mot, atomos, random.randint(1, 4))
            for _ in range(random.randint(1, 4))
        ]
        obtenido = modelos_tableau(mot)
        if (set(obtenido) != modelos_fuerza_bruta(mot)
                or len(obtenido) != len(set(obtenido))):
            malos += 1
            continue
        # Con átomos libres: cada rama abierta debe satisfacer las premisas
        # para cualquier completado de sus átomos libres.
        for mundo in resolver(mot, False).mundos:
            libres = mundo['libres']
            for vals in product((True, False), repeat=len(libres)):
                v = dict(mundo['asignaciones'])
                v.update(dict(zip(libres, vals)))
                if not all(mot.evaluar(p, v) for p in mot.premisas):
                    malos += 1
                    break
    chequear(malos == 0, f'600 bases aleatorias sin discrepancias ({malos} malas)')

    print()
    if fallos:
        print(f'❌ {len(fallos)} prueba(s) fallaron.')
        return 1
    print('✅ Todas las pruebas pasaron.')
    return 0


if __name__ == '__main__':
    if '--test' in sys.argv:
        sys.exit(autotest())
    if tk is None:
        print('tkinter no está disponible en este entorno.')
        sys.exit(1)
    root = tk.Tk()
    InterfazSistemasExpertos(root)
    root.mainloop()
