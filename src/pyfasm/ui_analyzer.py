"""
UI Structure Analyzer for PyFASM.
Extracts hierarchical UI trees, containers, layouts (grid/pack),
and data bindings from Python AST (CustomTkinter, Tkinter, PyQt).
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any


@dataclass
class UiWidgetSpec:
    widget_id: int
    widget_type: str
    name: str
    parent_container: str
    text: str = ""
    command: Optional[str] = None
    row: int = 0
    column: int = 0
    rowspan: int = 1
    columnspan: int = 1
    padx: Tuple[int, int] = (0, 0)
    pady: Tuple[int, int] = (0, 0)
    sticky: str = ""
    width: int = 0
    height: int = 0
    var_name: Optional[str] = None
    initial_value: str = ""
    values: List[str] = field(default_factory=list)


@dataclass
class UiContainerSpec:
    name: str
    parent_container: str
    row: int = 0
    column: int = 0
    padx: Tuple[int, int] = (0, 0)
    pady: Tuple[int, int] = (0, 0)
    sticky: str = ""
    corner_radius: int = 0
    fg_color: str = ""
    widgets: List[UiWidgetSpec] = field(default_factory=list)


@dataclass
class UiAppSpec:
    window_title: str = "PyFASM Application"
    window_width: int = 1100
    window_height: int = 700
    appearance_mode: str = "Dark"
    root_class_name: str = ""
    containers: Dict[str, UiContainerSpec] = field(default_factory=dict)
    widgets: List[UiWidgetSpec] = field(default_factory=list)
    has_canvas: bool = False
    plot_title: str = "График f(x)"
    plot_xlabel: str = "x"
    plot_ylabel: str = "y"
    solver_class_name: Optional[str] = None
    initial_vars: Dict[str, str] = field(default_factory=dict)


def _extract_kwarg_str(call: ast.Call, name: str) -> Optional[str]:
    for kw in call.keywords:
        if kw.arg == name:
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
    return None


def _extract_kwarg_int(call: ast.Call, name: str) -> Optional[int]:
    for kw in call.keywords:
        if kw.arg == name:
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
                return kw.value.value
    return None


def analyze_ui_structure(tree: ast.AST) -> Optional[UiAppSpec]:
    """Analyzes AST and builds complete UI specification tree if GUI application is detected."""
    app_cls = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            base_names = [b.id if isinstance(b, ast.Name) else getattr(b, "attr", "") for b in node.bases]
            if any(b in ("CTk", "Tk", "QMainWindow", "Window") for b in base_names) or "app" in node.name.lower():
                app_cls = node
                break

    if not app_cls:
        return None

    app_spec = UiAppSpec()
    app_spec.root_class_name = app_cls.name

    # 1. Discover Math / Solver Class if present
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name != app_cls.name:
            if "solve" in node.name.lower() or any(isinstance(m, ast.FunctionDef) and m.name == "solve" for m in node.body):
                app_spec.solver_class_name = node.name

    # 2. Window Properties and State Variables
    for item in app_cls.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        for node in ast.walk(item):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "title" and node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        app_spec.window_title = node.args[0].value
                if node.func.attr == "geometry" and node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        parts = node.args[0].value.lower().split("x")
                        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                            app_spec.window_width = int(parts[0])
                            app_spec.window_height = int(parts[1])
                if node.func.attr == "set_title" and node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        app_spec.plot_title = node.args[0].value
                if node.func.attr == "set_xlabel" and node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        app_spec.plot_xlabel = node.args[0].value
                if node.func.attr == "set_ylabel" and node.args:
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        app_spec.plot_ylabel = node.args[0].value
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "zip":
                if len(node.args) == 2:
                    keys, vals = node.args[0], node.args[1]
                    if isinstance(keys, ast.Constant) and isinstance(vals, ast.Tuple):
                        k_list = list(str(keys.value))
                        v_list = [v.value if isinstance(v, ast.Constant) else "" for v in vals.elts]
                        for k, v in zip(k_list, v_list):
                            app_spec.initial_vars[k] = str(v)

    # 3. Discover Containers (Frames / Cards)
    for item in app_cls.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        for stmt in item.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                var_name = stmt.targets[0].id
                if isinstance(stmt.value, ast.Call):
                    call_func = getattr(stmt.value.func, "attr", "")
                    if "frame" in call_func.lower():
                        c_spec = UiContainerSpec(name=var_name, parent_container="root")
                        for kw in stmt.value.keywords:
                            if kw.arg == "corner_radius" and isinstance(kw.value, ast.Constant):
                                c_spec.corner_radius = int(kw.value.value)
                        app_spec.containers[var_name] = c_spec

            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                c = stmt.value
                if isinstance(c.func, ast.Attribute) and c.func.attr in ("grid", "pack", "place"):
                    if isinstance(c.func.value, ast.Name) and c.func.value.id in app_spec.containers:
                        c_spec = app_spec.containers[c.func.value.id]
                        for kw in c.keywords:
                            if kw.arg == "row" and isinstance(kw.value, ast.Constant):
                                c_spec.row = int(kw.value.value)
                            elif kw.arg == "column" and isinstance(kw.value, ast.Constant):
                                c_spec.column = int(kw.value.value)
                            elif kw.arg == "sticky" and isinstance(kw.value, ast.Constant):
                                c_spec.sticky = str(kw.value.value)

    # 4. Discover Constant Loops (e.g. captions tuple)
    widget_id_gen = 1000
    captions_map = []
    for item in app_cls.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        for stmt in item.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == "captions":
                if isinstance(stmt.value, ast.Tuple):
                    for el in stmt.value.elts:
                        if isinstance(el, ast.Tuple) and len(el.elts) == 2:
                            c_k = el.elts[0].value if isinstance(el.elts[0], ast.Constant) else ""
                            c_v = el.elts[1].value if isinstance(el.elts[1], ast.Constant) else ""
                            captions_map.append((c_k, c_v))

    # 5. Extract Widgets from Chained Calls and Direct Assignments
    for item in app_cls.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        for stmt in item.body:
            # Chained calls: CTkLabel(...).grid(...)
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.func.attr in ("grid", "pack", "place"):
                    inner = call.func.value
                    if isinstance(inner, ast.Call):
                        w_type = getattr(inner.func, "attr", "").lower()
                        p_cont = inner.args[0].id if inner.args and isinstance(inner.args[0], ast.Name) else "root"
                        txt = _extract_kwarg_str(inner, "text") or ""
                        cmd = None
                        for kw in inner.keywords:
                            if kw.arg == "command" and isinstance(kw.value, ast.Attribute):
                                cmd = kw.value.attr
                        
                        r = _extract_kwarg_int(call, "row") or 0
                        col = _extract_kwarg_int(call, "column") or 0
                        stk = _extract_kwarg_str(call, "sticky") or ""

                        widget_id_gen += 1
                        w = UiWidgetSpec(
                            widget_id=widget_id_gen,
                            widget_type=w_type,
                            name=f"widget_{widget_id_gen}",
                            parent_container=p_cont,
                            text=txt,
                            command=cmd,
                            row=r,
                            column=col,
                            sticky=stk
                        )
                        app_spec.widgets.append(w)

            # Assigned widgets
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                tgt = stmt.targets[0]
                tgt_name = tgt.attr if isinstance(tgt, ast.Attribute) else (tgt.id if isinstance(tgt, ast.Name) else "")
                val = stmt.value
                if isinstance(val, ast.Call):
                    w_type = getattr(val.func, "attr", "").lower()
                    if any(t in w_type for t in ("label", "button", "entry", "textbox", "segmentedbutton", "canvas")):
                        p_cont = val.args[0].id if val.args and isinstance(val.args[0], ast.Name) else "root"
                        txt = _extract_kwarg_str(val, "text") or ""
                        cmd = None
                        vals = []
                        for kw in val.keywords:
                            if kw.arg == "command" and isinstance(kw.value, ast.Attribute):
                                cmd = kw.value.attr
                            elif kw.arg == "values" and isinstance(kw.value, ast.List):
                                vals = [e.value for e in kw.value.elts if isinstance(e, ast.Constant)]
                        widget_id_gen += 1
                        w = UiWidgetSpec(
                            widget_id=widget_id_gen,
                            widget_type=w_type,
                            name=tgt_name,
                            parent_container=p_cont,
                            text=txt,
                            command=cmd,
                            values=vals
                        )
                        app_spec.widgets.append(w)

            # Canvas detection
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                f_name = getattr(stmt.value.func, "id", "") or getattr(stmt.value.func, "attr", "")
                if "FigureCanvas" in f_name or "Canvas" in f_name:
                    app_spec.has_canvas = True

    # 6. Unroll Captions Loop if found
    if captions_map:
        for idx, (var_k, cap_v) in enumerate(captions_map):
            row_lbl = (idx + 2) * 2
            row_entry = row_lbl + 1
            widget_id_gen += 1
            app_spec.widgets.append(UiWidgetSpec(
                widget_id=widget_id_gen,
                widget_type="ctklabel",
                name=f"lbl_{var_k}",
                parent_container="side",
                text=f"{var_k}  ·  {cap_v}",
                row=row_lbl,
                column=0,
                sticky="w"
            ))
            widget_id_gen += 1
            init_val = app_spec.initial_vars.get(var_k, "")
            app_spec.widgets.append(UiWidgetSpec(
                widget_id=widget_id_gen,
                widget_type="ctkentry",
                name=f"entry_{var_k}",
                parent_container="side",
                text=init_val,
                var_name=var_k,
                initial_value=init_val,
                row=row_entry,
                column=0,
                sticky="ew"
            ))

    # 7. Re-link layout coordinates to named widgets
    for item in app_cls.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        for stmt in item.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                c = stmt.value
                if isinstance(c.func, ast.Attribute) and c.func.attr in ("grid", "pack", "place"):
                    t_name = c.func.value.attr if isinstance(c.func.value, ast.Attribute) else (c.func.value.id if isinstance(c.func.value, ast.Name) else "")
                    for w in app_spec.widgets:
                        if w.name == t_name:
                            w.row = _extract_kwarg_int(c, "row") or w.row
                            w.column = _extract_kwarg_int(c, "column") or w.column
                            w.sticky = _extract_kwarg_str(c, "sticky") or w.sticky

    return app_spec
