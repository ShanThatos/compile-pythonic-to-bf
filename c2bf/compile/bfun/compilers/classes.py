from c2bf.compile.bfun.compilers.utils import extend_label, new_label, parse_code
from c2bf.parser.ast import ASTNode


def transform_classes(root_ast: ASTNode):
    strings = getattr(root_ast, "strings", {})

    def transform_class(ast: ASTNode):
        if ast.name != "class_def":
            return
        
        class_name = ast.get("REF").literal.value
        fields = ast.get_all("class_field")
        funcs = ast.get_all("class_function")
        constructor = next((f for f in funcs if f.get("REF").literal.value == "$new"), None)

        class_lbl = new_label(ast, f"class_{class_name}")
        class_db_lbl = extend_label(ast, class_lbl, "db")

        structure_attr_names = [""]
        structure_attr_lbls = [class_name]
        instance_attrs = [f"    set this {class_lbl}"]
        for field in fields:
            attr_name = field.get("REF").literal.value
            structure_attr_names.append(attr_name)
            str_attr_lbl = strings[attr_name][1]
            structure_attr_lbls.append(str_attr_lbl)

            expr = field.get_all("expression")
            expr = expr[0].to_string() if expr else "0"
            set_field_code = [
                f"    r1 = {expr}",
                f"    r0 = this + {len(instance_attrs)}"
                f"    set r0 r1"
            ]
            instance_attrs.append("\n".join(set_field_code))
        for func in funcs:
            func.name = "function"
            func_name = func.get("REF").literal.value
            structure_attr_names.append(func_name)
            str_func_lbl = strings[func_name][1]
            structure_attr_lbls.append(str_func_lbl)

            func_lbl = f"{class_name}${func_name}"
            func.get("REF").literal.value = func_lbl

            make_caller_code = [
                f"    mov r0 this",
                f"    mov r1 {func_lbl}",
                f"    call __make_caller__",
                f"    r0 = this + {len(instance_attrs)}",
                f"    set r0 rv"
            ]
            instance_attrs.append("\n".join(make_caller_code))

        class_code = [f"\n# Class {class_name}"]

        class_code.append(f"\nvariadic func {class_name}(params) {{")
        class_code.append(f"    mov r0 {len(instance_attrs)}")
        class_code.append(f"    call __malloc__")
        class_code.append(f"    mov this rv")
        class_code.append(f"    setf this 1")
        class_code.extend(instance_attrs)
        if constructor:
            class_code.append(f"    call {constructor.get('REF').literal.value}")
        class_code.append(f"    return this")
        class_code.append(f"}}")

        class_code.append(f"{class_lbl}: ")
        class_code.append(f"{class_db_lbl}: {', '.join('0' for _ in range(len(structure_attr_lbls) + 1))}")
        class_code.append(f"inc {class_lbl}")
        for i, attr in enumerate(structure_attr_lbls):
            if i > 0:
                class_code.append(f"inc {class_lbl}")
            class_code.append(f"set {class_lbl} {attr}")
        class_code.append(f"sub {class_lbl} {len(structure_attr_lbls) - 1}")

        for func in funcs:
            setattr(func, "class_structure", structure_attr_names)

        return parse_code("\n" + "\n".join(class_code)).children + funcs

    ASTNode.transform(root_ast, transform_class)
