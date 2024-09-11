from datetime import datetime, timedelta
from flask_mysqldb import MySQL
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from datetime import datetime
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, session
import mysql.connector
from werkzeug.security import check_password_hash


app = Flask(__name__, static_folder='static', template_folder='template')


# Configura la conexión a la base de datos MySQL
app.config['MYSQL_HOST'] = "localhost"
app.config['MYSQL_USER'] = "root"
app.config['MYSQL_PASSWORD'] = "12345"
app.config['MYSQL_DB'] = "bd_gimnasio2"
mysql = MySQL(app)

# Inicializar sesion
app.secret_key = 'mysecretkey'


# Ruta para la página de inicio de sesión
@app.route('/', methods=['GET', 'POST'])
def login():
    identificacion = None
    contrasena = None
    if request.method == 'POST':
        identificacion = request.form['identificacion']
        contrasena = request.form['contrasena']

        # Consulta para buscar en la tabla miembro
        cur = mysql.connection.cursor()
        cur.execute("SELECT IDENTIFICACION, CONTRASENA FROM miembros WHERE IDENTIFICACION = %s", (identificacion,))
        miembro = cur.fetchone()
        cur.close()

        # Consulta para buscar en la tabla empleado
        cur = mysql.connection.cursor()
        cur.execute("SELECT IDENTIFICACION_EMPLEADO, CONTRASENA, ID_SALARIO_EMPLE FROM empleado WHERE IDENTIFICACION_EMPLEADO = %s", (identificacion,))
        empleado = cur.fetchone()
        cur.close()

        if miembro and contrasena == miembro[1]:
            # Iniciar sesión como miembro
            session['identificacion'] = miembro[0]
            session['rol'] = 'miembro'
            # Almacena información del miembro en la sesión
            session['info_usuario'] = obtener_info_miembro(miembro[0])
            return redirect(url_for('miembro'))

        elif empleado and contrasena == empleado[1]:
            # Obtener el rol del empleado
            cur = mysql.connection.cursor()
            cur.execute("SELECT CARGO FROM salario_empleado WHERE ID_SALARIO_EMPLE = %s", (empleado[2],))
            cargo = cur.fetchone()
            cur.close()

            if cargo:
                # Iniciar sesión como administrador o instructor según el cargo
                session['identificacion'] = empleado[0]
                session['rol'] = 'administrador' if cargo[0] == 'Administrador' else 'instructor'
                # Almacena información del empleado en la sesión
                session['info_usuario'] = obtener_info_empleado(empleado[0])
                # Redirige a la vista correspondiente
                if cargo[0] == 'Administrador':
                    return redirect(url_for('administrador'))
                elif cargo[0] == 'Instructor':
                    return redirect(url_for('entrenador'))

        flash('Credenciales incorrectas. Intenta de nuevo.')

    return render_template('login.html')

def obtener_info_miembro(identificacion):
    cur = mysql.connection.cursor()
    cur.execute("SELECT IDENTIFICACION, NOMBRE, APELLIDO, EDAD, CORREO, TELEFONO, CONTRASENA, ESTADO FROM miembros WHERE IDENTIFICACION = %s", (identificacion,))
    info_miembro = cur.fetchone()
    cur.close()
    return info_miembro

def obtener_info_empleado(identificacion):
    cur = mysql.connection.cursor()
    cur.execute("SELECT IDENTIFICACION_EMPLEADO, NOMBRE, APELLIDO, EDAD, CORREO, GENERO, CONTRASENA, ESPECIALIDAD, HORARIO, ESTADO FROM empleado WHERE IDENTIFICACION_EMPLEADO = %s", (identificacion,))
    info_empleado = cur.fetchone()
    cur.close()
    return info_empleado

# Ruta para el panel del miembro
@app.route('/miembro')
def miembro():
    identificacion = session.get('identificacion')
    info_miembro = obtener_info_miembro(identificacion)

    if info_miembro:
        # Obtener las reservas del miembro actual
        cur = mysql.connection.cursor()
        cur.execute('''
    SELECT c.*, r.ID_RESERVA, e.NOMBRE AS NOMBRE_INSTRUCTOR
    FROM clase c
    JOIN reserva_clase r ON c.ID_CLASE = r.ID_CLASE
    JOIN empleado e ON c.INSTRUCTOR = e.IDENTIFICACION_EMPLEADO
    WHERE r.IDENTIFICACION_MIEMBRO = %s
''', (identificacion,))
        reservas = cur.fetchall()
        cur.execute('''
    SELECT rm.*, m.NOMBRE AS nombre_maquina
    FROM reserva_maquina rm
    JOIN maquina m ON rm.ID_MAQUINA = m.ID_MAQUINA
    WHERE rm.IDENTIFICACION_MIEMBRO = %s
''', (identificacion,))
        reservasm = cur.fetchall()
        cur.close()


        return render_template('cliente/miembro.html', info_miembro=info_miembro, reservas=reservas, reservasm=reservasm)
    else:
        # Manejar el caso en que no se encuentre la información del miembro
        flash('Error al obtener la información del miembro.')
        return redirect(url_for('login'))


# Ruta para el panel del administrador (administrador)
@app.route('/administrador')
def administrador():
    return render_template('administrador/administrador.html')

@app.route('/gestion_usuarios')
def gestion_usuarios():
     return render_template('administrador/gestion_usuarios.html')

@app.route('/gestion_maquinas')
def gestion_maquinas():
     return render_template('gestion_maquinas.html')

@app.route('/gestion_membresias')
def gestion_membresias():
     return render_template('administrador/gestion_membresias.html')
 
@app.route('/gestion_instructores')
def gestion_instructores():
     return render_template('administrador/gestion_instructores.html')

#plan de trabajo
@app.route('/planes_trabajo_ins')
def planes_trabajo_ins():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT *
                FROM miembros
                WHERE ID_PLAN IS NULL
                AND ID_MEMBRESIA <> 0
                AND ESTADO <> 0
                AND ID_ESTADO_MEM <> 0
                ;
                """)
    data = cur.fetchall()
    mysql.connection.commit()
    cur.close()
    return render_template('planes_trabajo_ins.html', info_miembro=data)

# progreso plan de trabajo 
@app.route('/proceso_plan_trabajo')
def proceso_plan_trabajo():
    identificacion = session.get('identificacion')
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT asignacion.*, empleado.NOMBRE AS nombre_empleado 
                FROM asignacion_pla_trabajo asignacion 
                JOIN empleado ON asignacion.IDENTIFICACION_EMPLEADO = 
                empleado.IDENTIFICACION_EMPLEADO 
                WHERE asignacion.ID_MIEMBRO_PLAN = %s;
            """, (identificacion,))
    
    data = cur.fetchall()
    cur.execute("""
    SELECT *
    FROM progreso_plan_trabajo
    WHERE IDENTIFICACION_MIEMBRO = %s;
    """, (identificacion,))
    dataprogreso = cur.fetchall()
    cur.close()
    print(data)
    # Verificar si hay datos en 'data'
    if not data:
        flash ('No hay plan trabajo para este miembro.')
        return render_template('cliente/proceso_plan_trabajo.html', )

    mysql.connection.commit()
    return render_template('cliente/proceso_plan_trabajo.html', rows=data, progreso=dataprogreso)

# Ruta para ingresar el progreso del plan de trabajo
@app.route('/ingresar_progreso/<id>', methods=['GET', 'POST'])
def ingresar_progreso(id):
    identificacion = session.get('identificacion')

    # Verifica si se encontró el ID_ASIG_PLAN
    if id is None:
        flash('No se encontró el plan de trabajo para ingresar progreso.', 'danger')
        return redirect(url_for('miembro'))

    if request.method == 'POST':
        fecha_avance = request.form.get('fecha_avance')
        descripcion_avance = request.form.get('descripcion_avance')
        horas_trabajadas = request.form.get('horas_trabajadas')

        # Insertar en la base de datos
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO progreso_plan_trabajo (ID_ASIG_PLAN, IDENTIFICACION_MIEMBRO, FECHA_AVANCE, DESCRIPCION_AVANCE, HORAS_TRABAJADAS)
                VALUES (%s, %s, %s, %s, %s)
            """, (id, identificacion, fecha_avance, descripcion_avance, horas_trabajadas))
            
            mysql.connection.commit()
            cur.close()
            flash('Progreso registrado correctamente.', 'success')
            return redirect(url_for('proceso_plan_trabajo'))
        except Exception as e:
            flash(f'Error al registrar el progreso: {str(e)}', 'danger')

    return render_template('cliente/ingresar_progreso.html', id=id )


#vista de asignar plan de trabajo
@app.route('/vista_asignar_plan_trabajo/<idm>')
def vista_asignar_plan_trabajo(idm):
    cur = mysql.connection.cursor()
    cur.execute("""SELECT *
                FROM planes_trabajo
                """)
    data = cur.fetchall()
    global idmiembro 
    idmiembro = idm
    mysql.connection.commit()
    return render_template('vista_asignar_plan_trabajo.html', planes=data)

# accion de asignar plan de trabajo
@app.route("/asignar/<id>", methods=['POST'])
def getidclase(id):
    identificacion = session.get('identificacion')

    if request.method == 'POST':
        fechainicio = request.form['fecha_inicio']
        fechafin = request.form['fecha_fin']
        try:
            cur = mysql.connection.cursor()
            cur.execute('SET foreign_key_checks = 0;')
            cur.execute("""UPDATE miembros SET ID_PLAN = %s WHERE IDENTIFICACION = %s""", (id, idmiembro))
            cur.execute("""INSERT INTO asignacion_pla_trabajo (ID_MIEMBRO_PLAN, ID_PLAN, 
                        IDENTIFICACION_EMPLEADO, FECHA_INICIO, FECHA_FIN) VALUES (%s, %s, %s, %s, %s)""",
                        (idmiembro, id, identificacion, fechainicio, fechafin))
            mysql.connection.commit()
            flash('Plan de trabajo asignado correctamente')
            return redirect(url_for('planes_trabajo_ins'))
        except Exception as e:
            # Si hay algún error, puedes imprimirlo para depuración
            print(f"Error al insertar en la base de datos: {str(e)}")
            flash('Error al asignar plan de trabajo')
            mysql.connection.rollback()  # Revertir la transacción
        finally:
            cur.close()

    # Agrega un retorno para el caso en que la solicitud no sea POST
    return "Algo para mostrar si la solicitud no es POST"

# perfil de miembro
@app.route('/perfil')
def perfil():
    identificacion = session.get('identificacion')
    info_miembro = obtener_info_miembro(identificacion)
    if info_miembro:
        return render_template('cliente/perfil.html', info_miembro=info_miembro)
    else:
        # Manejar el caso en el que no se encuentre la información del miembro
        flash('Error al obtener la información del miembro.')

# perfil de instructor
@app.route('/perfil_instructor')
def perfil_instructor():
    identificacion = session.get('identificacion')
    info_empleado = obtener_info_empleado(identificacion)
    if info_empleado:
        return render_template('entrenador/perfil_instructor.html', info_empleado=info_empleado)
    else:
        # Manejar el caso en el que no se encuentre la información del miembro
        flash('Error al obtener la información del miembro.')
    
# formulario de edicion datos personales de miembro
@app.route('/info_personal_user')
def info_personal_user():
    identificacion = session.get('identificacion')
    info_miembro = obtener_info_miembro(identificacion)
    if info_miembro:
        return render_template('cliente/info_personal_user.html', info_miembro=info_miembro)
    else:
        flash('Error al obtener la información del miembro.')
        return redirect(url_for('perfil'))

# formulario de edicion datos personales de instructor
@app.route('/editar_info_personal_ins')
def editar_info_personal_ins():
    identificacion = session.get('identificacion')
    info_empleado = obtener_info_empleado(identificacion)
    if info_empleado:
        return render_template('entrenador/editar_info_personal_ins.html', info_empleado=info_empleado)
    else:
        flash('Error al obtener la información del instructor.')
        return redirect(url_for('perfil_instructor'))

# accion de editar datos miembro desde rol miembro
@app.route("/actualizar/<id>", methods=['POST'])
def getidentificacion(id):
    identificacion = session.get('identificacion')
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        edad = request.form['edad']
        correo = request.form['correo']
        telefono = request.form['telefono']

        cur = mysql.connection.cursor()
        cur.execute('UPDATE miembros SET NOMBRE = %s, APELLIDO = %s, EDAD = %s, CORREO = %s, TELEFONO = %s WHERE IDENTIFICACION = %s',
                    (nombre, apellido, edad, correo, telefono, id))
        mysql.connection.commit()
        info_empleado = obtener_info_empleado(identificacion)
        flash('Información editada correctamente')
        return redirect(url_for('info_personal_user'))
    
# accion de editar datos instructor desde rol instructor
@app.route("/actualizar_ins/<id>", methods=['POST'])
def getidentificacion_ins(id):
    identificacion = session.get('identificacion')
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        edad = request.form['edad']
        correo = request.form['correo']

        cur = mysql.connection.cursor()
        cur.execute('UPDATE empleado SET NOMBRE = %s, APELLIDO = %s, EDAD = %s, CORREO = %s WHERE IDENTIFICACION_EMPLEADO = %s',
                    (nombre, apellido, edad, correo, id))
        mysql.connection.commit()
        flash('Información editada correctamente')
        return redirect(url_for('editar_info_personal_ins'))

# cambiar contraseña rol miembro
@app.route('/cambio_contrasena_user')
def cambio_contrasena_user():
    identificacion = session.get('identificacion')
    info_miembro = obtener_info_miembro(identificacion)
    if info_miembro:
        return render_template('cliente/cambio_contrasena_user.html', info_miembro=info_miembro)
    else:
        # Manejar el caso en el que no se encuentre la información del miembro
        flash('Error al obtener la información del miembro.')

# cambiar contraseña rol instructor
@app.route('/cambio_contrasena_ins')
def cambio_contrasena_ins():
    identificacion = session.get('identificacion')
    info_empleado = obtener_info_empleado(identificacion)
    if info_empleado:
        return render_template('entrenador/cambio_contrasena_ins.html', info_empleado=info_empleado)
    else:
        # Manejar el caso en el que no se encuentre la información del miembro
        flash('Error al obtener la información del miembro.')

# accion de editar contraseña miembro desde rol miembro
@app.route("/actualizarcontrasena/<id>", methods=['POST'])
def actualizar_contrasena(id):
    info_miembro = obtener_info_miembro(id)
    if request.method == 'POST':
        # Obtener las contraseñas del formulario
        current_password = request.form['currend_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        print('CONTRASEÑA ACTUAL:' + info_miembro[6])
        # Validar que la contraseña actual sea correcta
        if current_password != info_miembro[6]:
            flash('La contraseña actual no es correcta.')
            return redirect(url_for('cambio_contrasena_user'))

        # Validar que la nueva contraseña y la confirmación coincidan
        if new_password != confirm_password:
            flash('La nueva contraseña y la confirmación no coinciden.')
            return redirect(url_for('cambio_contrasena_user'))

        # Realizar la actualización de la contraseña en la base de datos
        cur = mysql.connection.cursor()
        cur.execute('UPDATE miembros SET CONTRASENA = %s WHERE IDENTIFICACION = %s',
                    (new_password, id))
        mysql.connection.commit()
        flash('Contraseña actualizada correctamente.')
        info_miembro = obtener_info_miembro(id)

    return redirect(url_for('cambio_contrasena_user'))

# accion de editar contraseña miembro desde rol miembro
@app.route("/actualizarcontrasenains/<id>", methods=['POST'])
def actualizar_contrasena_ins(id):
    info_empleado = obtener_info_empleado(id)
    if request.method == 'POST':
        # Obtener las contraseñas del formulario
        current_password = request.form['currend_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        print('CONTRASEÑA ACTUAL:' + info_empleado[6])
        # Validar que la contraseña actual sea correcta
        if current_password != info_empleado[6]:
            flash('La contraseña actual no es correcta.')
            return redirect(url_for('cambio_contrasena_ins'))

        # Validar que la nueva contraseña y la confirmación coincidan
        if new_password != confirm_password:
            flash('La nueva contraseña y la confirmación no coinciden.')
            return redirect(url_for('cambio_contrasena_ins'))

        # Realizar la actualización de la contraseña en la base de datos
        cur = mysql.connection.cursor()
        cur.execute('UPDATE empleado SET CONTRASENA = %s WHERE IDENTIFICACION_EMPLEADO = %s',
                    (new_password, id))
        mysql.connection.commit()
        flash('Contraseña actualizada correctamente.')
        info_empleado = obtener_info_empleado(id)

    return redirect(url_for('cambio_contrasena_ins'))

@app.route('/membresia_user')
def membresia_user():
    return render_template('membresia_user.html')

# Ruta para el panel del entrenador (entrenador)
@app.route('/entrenador')
def entrenador():
    identificacion = session.get('identificacion')
    info_empleado = obtener_info_empleado(identificacion)

    if info_empleado:
        # Obtener las reservas del miembro actual
        cur = mysql.connection.cursor()
        cur.execute('''
                    SELECT asignacion_pla_trabajo.*, planes_trabajo.NOMBRE AS NOMBRE_PLAN, planes_trabajo.DESCRIPCION AS DESCRIPCION_PLAN
                    FROM asignacion_pla_trabajo
                    JOIN planes_trabajo ON asignacion_pla_trabajo.ID_PLAN = planes_trabajo.ID_PLAN
                    WHERE asignacion_pla_trabajo.IDENTIFICACION_EMPLEADO = %s;

                ''', (identificacion,))
        planestrabajo = cur.fetchall()
        cur.close()

        return render_template('entrenador/entrenador.html', info_empleado=info_empleado, planestrabajo=planestrabajo)
    else:
        # Manejar el caso en que no se encuentre la información del miembro
        flash('Error al obtener la información del miembro.')
        return redirect(url_for('login'))

# Ruta para el panel de ver historial de maquinaria
@app.route('/vista_historial_maquinaria')
def ver_historial():
    return render_template('vista_historial_maquinaria.html')

# Ruta para el panel de nosotros
@app.route('/NOSOTROS')
def NOSOTROS():
    return render_template('NOSOTROS.html')

@app.route('/CONTACTOS')
def CONTACTOS():
    return render_template('CONTACTOS.html')

#estado membresia
@app.route('/estado_membresia', methods=['GET', 'POST'])
def estado_membresia():
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT 
        miembros.IDENTIFICACION, 
        miembros.NOMBRE, 
        miembros.APELLIDO, 
        miembros.EDAD,
        miembros.ESTADO,
        estado_membresia.ESTADO,
        estado_membresia.FECHA_INICIO,
        estado_membresia.FECHA_FIN,
        membresia_precios.TIPO,
        membresia_precios.COSTO
    FROM miembros
    JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
    JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
    """)

    membresias = cur.fetchall()
    cur.close()

    return render_template('administrador/estado_membresia.html', membresias=membresias)

#vista cambiar estado membresia
@app.route('/vista_cambiar_estado_membresia/<cedula>', methods=['GET', 'POST'])
def vista_cambiar_estado_membresia(cedula):
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT 
        miembros.IDENTIFICACION, 
        miembros.NOMBRE, 
        miembros.APELLIDO, 
        miembros.EDAD,
        miembros.ESTADO,
        estado_membresia.ESTADO,
        estado_membresia.FECHA_INICIO,
        estado_membresia.FECHA_FIN,
        membresia_precios.TIPO,
        membresia_precios.COSTO
    FROM miembros
    JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
    JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
    
    WHERE miembros.IDENTIFICACION = %s
    """, (cedula,))

    membresias = cur.fetchall()
    
    if request.method == 'POST':
        # Obtener el ID_ESTADO_MEM, el estado actual y el tipo de membresia del miembro
        cur.execute("""
            SELECT miembros.ID_ESTADO_MEM, estado_membresia.ESTADO, miembros.ID_MEMBRESIA
            FROM miembros
            JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
            JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
            WHERE miembros.IDENTIFICACION = %s
            """, (cedula,))
        id_estado_mem, estado_actual, tipo_membresia = cur.fetchone()

        nuevo_estado = 0 if estado_actual == 1 else 1

        # Actualizar la tabla estado_membresia
        if estado_actual == 1:
            cur.execute("""
                UPDATE estado_membresia
                SET ESTADO = %s, FECHA_INICIO = NULL, FECHA_FIN = NULL
                WHERE ID_ESTADO_MEM = %s
                """, (nuevo_estado, id_estado_mem))
        else:
            fecha_inicio = datetime.now()
            if tipo_membresia == 1:
                fecha_fin = fecha_inicio + timedelta(days=30)
            elif tipo_membresia == 2:
                fecha_fin = fecha_inicio + timedelta(days=365)
            elif tipo_membresia == 3:
                fecha_fin = fecha_inicio + timedelta(days=7)
            fecha_inicio_f = fecha_inicio.strftime('%Y-%m-%d')
            fecha_fin_f = fecha_fin.strftime('%Y-%m-%d')
            cur.execute("""
                UPDATE estado_membresia
                SET ESTADO = %s, FECHA_INICIO = %s, FECHA_FIN = %s
                WHERE ID_ESTADO_MEM = %s
                """, (nuevo_estado, fecha_inicio_f, fecha_fin_f, id_estado_mem))
            
        mysql.connection.commit()  
       
    flash('estado modificado correctamente')
    cur.close()
    return render_template('administrador/vista_cambiar_estado_membresia.html', membresias=membresias) 
    
#listado membresia administrador
@app.route('/listado_membresia')
def listado_membresia():
    
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT 
        miembros.IDENTIFICACION, 
        miembros.NOMBRE, 
        miembros.APELLIDO, 
        miembros.EDAD,
        miembros.ESTADO,
        estado_membresia.ESTADO AS estado_membresia,
        estado_membresia.FECHA_INICIO,
        estado_membresia.FECHA_FIN,
        membresia_precios.TIPO,
        membresia_precios.COSTO
    FROM miembros
    LEFT JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
    LEFT JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
""",)
    membresias = cur.fetchall()
    cur.close()

    return render_template('administrador/listado_membresia.html', membresias=membresias)

#vista editar membresia administrador
@app.route('/editar_membresia')
def editar_membresia():
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT 
        miembros.IDENTIFICACION, 
        miembros.NOMBRE, 
        miembros.APELLIDO, 
        miembros.EDAD,
        miembros.ESTADO,
        estado_membresia.ESTADO AS estado_membresia,
        estado_membresia.FECHA_INICIO,
        estado_membresia.FECHA_FIN,
        membresia_precios.TIPO,
        membresia_precios.COSTO
    FROM miembros
    JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
    JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
""")
    
    membresias = cur.fetchall()
    cur.close()

    return render_template('administrador/editar_membresia.html', membresias=membresias)

#accion editar membresia
@app.route('/vista_editar_membresia/<cedula>', methods=['GET', 'POST'])
def vista_editar_membresia(cedula):
    
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT 
        miembros.IDENTIFICACION, 
        miembros.NOMBRE, 
        miembros.APELLIDO, 
        miembros.EDAD,
        miembros.ESTADO,
        estado_membresia.ESTADO AS estado_membresia,
        estado_membresia.FECHA_INICIO,
        estado_membresia.FECHA_FIN,
        membresia_precios.COSTO
    FROM miembros
    JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
    JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
    WHERE miembros.IDENTIFICACION = %s
""", (cedula,))
    miembro = cur.fetchall()
    
    
    if request.method == 'POST':
        tipo = request.form['tipo']
        cur.execute("""
        UPDATE miembros
        SET ID_MEMBRESIA = %s
        WHERE IDENTIFICACION = %s
        """, (tipo, cedula))
        mysql.connection.commit()
        flash('miembro editado correctamente')
        return redirect(url_for('editar_membresia'))
    cur.close()
    return render_template('administrador/vista_editar_membresia.html', miembro=miembro)

#vista principal de asignar membresia
@app.route('/asignar_membresia')
def asignar_membresia():
    id_estado_mem = 0
    estado_miembro = 1
    
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT 
        miembros.IDENTIFICACION, 
        miembros.NOMBRE, 
        miembros.APELLIDO, 
        miembros.EDAD,
        miembros.ESTADO,
        estado_membresia.ESTADO AS estado_membresia,
        estado_membresia.FECHA_INICIO,
        estado_membresia.FECHA_FIN,
        membresia_precios.TIPO,
        membresia_precios.COSTO
    FROM miembros
    LEFT JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
    LEFT JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
    WHERE miembros.ID_ESTADO_MEM = %s AND miembros.ESTADO = %s
""", (id_estado_mem, estado_miembro,))
    
    membresias = cur.fetchall()
    cur.close()

    return render_template('administrador/asignar_membresia.html', membresias=membresias)

#vista secundaria de asignar membresia
@app.route('/vista_asignar_membresia/<cedula>', methods=['GET', 'POST'])
def vista_asignar_membresia(cedula):
    
    id_estado_mem = 1
    
    cur = mysql.connection.cursor()
    cur.execute("""
    SELECT 
        miembros.IDENTIFICACION, 
        miembros.NOMBRE, 
        miembros.APELLIDO, 
        miembros.EDAD,
        miembros.ESTADO
    FROM miembros
    LEFT JOIN estado_membresia ON miembros.ID_ESTADO_MEM = estado_membresia.ID_ESTADO_MEM
    LEFT JOIN membresia_precios ON miembros.ID_MEMBRESIA = membresia_precios.ID_MEMBRESIA
    WHERE miembros.IDENTIFICACION = %s
""", (cedula,))
    miembro = cur.fetchall()
    
    if request.method == 'POST':
        tipo = request.form['tipo']
        fecha_inicio = datetime.strptime(request.form['fecha_inicio'], '%Y-%m-%d')
        estado_membresia = 1
        
        # Calcular la fecha_fin según el tipo de membresía
        if tipo == '1':
            fecha_fin = fecha_inicio + timedelta(days=30)
        elif tipo == '2':
            fecha_fin = fecha_inicio + timedelta(days=365)
        elif tipo == '3':
            fecha_fin = fecha_inicio + timedelta(days=7)
        
        # Crear un nuevo registro en la tabla estado_membresia
        cur.execute("""
            INSERT INTO estado_membresia (ESTADO, FECHA_INICIO, FECHA_FIN, ID_MEMBRESIA)
            VALUES (%s, %s, %s, %s)
        """, (estado_membresia, fecha_inicio, fecha_fin, tipo))
        id_estado_mem = cur.lastrowid  # Obtener el ID del último registro insertado
        
        # Actualizar la tabla miembros
        cur.execute("""
            UPDATE miembros
            SET ID_MEMBRESIA = %s, ID_ESTADO_MEM = %s
            WHERE IDENTIFICACION = %s
            """, (tipo, id_estado_mem, cedula))

        mysql.connection.commit()
        flash('miembro asignado correctamente')
        return redirect(url_for('asignar_membresia'))
    cur.close()
    return render_template('administrador/vista_asignar_membresia.html', miembro=miembro)

#vista de reservas desde miembro
@app.route('/reservas_miembro')
def reservas_miembro():
    identificacion = session.get('identificacion')
    info_miembro = obtener_info_miembro(identificacion)
    if info_miembro:
        return render_template('cliente/reservas_miembro.html', info_miembro=info_miembro)
    else:
        # Manejar el caso en el que no se encuentre la información del miembro
        flash('Error al obtener la información del miembro.')

#reservar clase desde miembro
@app.route('/reservar_clase')
def reservar_clase():
        cur = mysql.connection.cursor()
        cur.execute("SELECT clase.*, empleado.NOMBRE AS NOMBRE_INSTRUCTOR FROM clase INNER JOIN empleado ON clase.INSTRUCTOR = empleado.IDENTIFICACION_EMPLEADO")  
        rows = cur.fetchall()
        cur.close()
        return render_template('cliente/reservar_clase.html', rows=rows)


#accion de reservar clase desde miembro
@app.route("/accion_reservar_clase/<id>", methods=['GET', 'POST'])
def accion_reservar_clase(id):
    identificacion = session.get('identificacion')

    try:
        # Verificar si el usuario ya ha reservado la clase
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM reserva_clase WHERE ID_CLASE = %s AND IDENTIFICACION_MIEMBRO = %s',
                    (id, identificacion))
        existing_reservation = cur.fetchone()

        if existing_reservation:
            flash('Ya has reservado esta clase anteriormente.')
        else:

            cur.execute("SELECT COUNT(*) FROM reserva_clase WHERE IDENTIFICACION_MIEMBRO = %s", (identificacion,))
            cantidad_reservas = cur.fetchone()[0]
            LIMITE_RESERVAS = 5

            if cantidad_reservas >= LIMITE_RESERVAS:
                flash('No se pueden hacer más de 5 reservas.')
                # Puedes redirigir al usuario a una página de error o a donde prefieras
            else:
                cur.execute('START TRANSACTION')

                # Realizar la inserción en la tabla reserva_clase
                cur.execute('INSERT INTO reserva_clase (ID_CLASE, IDENTIFICACION_MIEMBRO) VALUES (%s, %s)',
                            (id, identificacion))

                # Confirmar la transacción
                cur.execute('COMMIT')

                flash('Clase agendada correctamente.')

    except Exception as e:
        # Manejar cualquier excepción que pueda ocurrir durante la transacción
        cur.execute('ROLLBACK')
        flash(f'Error al agendar la clase: {str(e)}')

    finally:
        # Cerrar el cursor después de realizar la operación
        if cur:
            cur.close()

    return redirect(url_for('reservar_clase'))

  
#reservar maquina desde miembro
@app.route("/reservar_maquina", methods=['GET', 'POST'])
def reservar_maquina():
        cur = mysql.connection.cursor()
        cur.execute("""SELECT m.*, e.NOMBRE AS estado_nombre FROM maquina m 
                    JOIN estado_maquinaria e ON m.ID_ESTADO_MAQUINA = e.ID_ESTADO_MAQUINA WHERE e.NOMBRE = 1
                    """)  
        rows = cur.fetchall()
        cur.close()
        return render_template('cliente/reservar_maquina.html', rows=rows)

from MySQLdb import IntegrityError

# ...

# Reservar máquina desde miembro
@app.route('/vista_reservar_maquina/<id>', methods=['GET', 'POST'])
def vista_reservar_maquina(id):
        
    identificacion = session.get('identificacion')

    if request.method == 'POST':
        identificacion = session.get('identificacion')
        fecha = request.form.get('fecha')
        horainicio = request.form.get('horainicio')
        horafin = request.form.get('horafin')

        try:
            # Verificar si el usuario ya ha reservado la máquina
            cur = mysql.connection.cursor()
            cur.execute('SELECT * FROM reserva_maquina WHERE ID_MAQUINA = %s AND IDENTIFICACION_MIEMBRO = %s',
                        (id, identificacion))
            existing_reservations = cur.fetchall()

            if existing_reservations:
                flash('Ya has reservado esta máquina anteriormente.')
                return redirect(url_for('reservar_maquina'))
            else:
                cur.execute("SELECT COUNT(*) FROM reserva_maquina WHERE IDENTIFICACION_MIEMBRO = %s", (identificacion,))
                cantidad_reservas = cur.fetchone()[0]
                LIMITE_RESERVAS = 5

                if cantidad_reservas >= LIMITE_RESERVAS:
                    flash('No se pueden hacer más de 5 reservas.')
                    return redirect(url_for('reservar_maquina'))
                else:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        'INSERT INTO reserva_maquina (ID_MAQUINA, IDENTIFICACION_MIEMBRO, FECHA, HORA_INICIO, HORA_FIN) VALUES (%s, %s, %s, %s, %s)',
                        (id, identificacion, fecha, horainicio, horafin)
                    )
                    mysql.connection.commit()
                    cur.close()
                    flash('Reserva realizada correctamente.')
                    return redirect(url_for('reservar_maquina'))
        except IntegrityError as e:
            flash('Error: Ya has reservado esta máquina anteriormente.')
            return redirect(url_for('reservar_maquina'))
        except Exception as e:
            flash(f'Error al realizar la reserva: {str(e)}')
            return redirect(url_for('reservar_maquina'))
    else:
        fecha = None
        horainicio = None
        horafin = None
        cur = mysql.connection.cursor()
        cur.execute("""SELECT m.*, e.NOMBRE AS estado_nombre 
                    FROM maquina m 
                    JOIN estado_maquinaria e ON m.ID_ESTADO_MAQUINA = e.ID_ESTADO_MAQUINA 
                    WHERE m.ID_MAQUINA = %s 
                    """, (id,))
        rows = cur.fetchall()
        cur.close()
        return render_template('cliente/vista_reservar_maquina.html', rows=rows)

# Acción de reservar máquina desde miembro
@app.route("/accion_reservar_maquina/<id>", methods=['GET', 'POST'])
def accion_reservar_maquina(id):
    identificacion = session.get('identificacion')

    if request.method == 'POST':
        identificacion = session.get('identificacion')
        fecha = request.form.get('fecha')
        horainicio = request.form.get('horainicio')
        horafin = request.form.get('horafin')

    try:
        # Verificar si el usuario ya ha reservado la máquina
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM reserva_maquina WHERE ID_MAQUINA = %s AND IDENTIFICACION_MIEMBRO = %s',
                    (id, identificacion))
        existing_reservations = cur.fetchall()

        if existing_reservations:
            flash('Ya has reservado esta máquina anteriormente.')
        else:
            cur.execute("SELECT COUNT(*) FROM reserva_maquina WHERE IDENTIFICACION_MIEMBRO = %s", (identificacion,))
            cantidad_reservas = cur.fetchone()[0]
            LIMITE_RESERVAS = 5

            if cantidad_reservas >= LIMITE_RESERVAS:
                flash('No se pueden hacer más de 5 reservas.')
            else:
                cur = mysql.connection.cursor()
                cur.execute(
                'INSERT INTO reserva_maquina (ID_MAQUINA, IDENTIFICACION_MIEMBRO, FECHA, HORA_INICIO, HORA_FIN) VALUES (%s, %s, %s, %s, %s)',
                (id, identificacion, fecha, horainicio, horafin)
            )
            mysql.connection.commit()
            cur.close()
            flash('Reserva realizada correctamente.')
            return redirect(url_for('reservas_miembro'))
    except Exception as e:
                flash(f'Error al realizar la reserva: {str(e)}')
                return redirect(url_for('reservar_maquina'))


#mostrar plan de trabajo de miembro
@app.route('/plan_de_trabajo_miembro')
def plan_de_trabajo_miembro():
        identificacion = session.get('identificacion')
        info_miembro = obtener_info_miembro(identificacion)
        cur = mysql.connection.cursor()
        cur.execute("""SELECT asignacion_pla_trabajo.*, planes_trabajo.NOMBRE AS NOMBRE_PLAN, planes_trabajo.DESCRIPCION AS DESCRIPCION_PLAN, empleado.NOMBRE AS NOMBRE_EMPLEADO
                FROM asignacion_pla_trabajo
                JOIN planes_trabajo ON asignacion_pla_trabajo.ID_PLAN = planes_trabajo.ID_PLAN
                JOIN empleado ON asignacion_pla_trabajo.IDENTIFICACION_EMPLEADO = empleado.IDENTIFICACION_EMPLEADO
                WHERE asignacion_pla_trabajo.ID_MIEMBRO_PLAN = %s;
                """, (identificacion,))  
        rows = cur.fetchall()
        cur.close()
        return render_template('cliente/plan_de_trabajo_miembro.html', rows=rows, info_miembro=info_miembro)

#vista estdo de membresia desde miembro
@app.route('/miembro_estado_membresia')
def miembro_estado_membresia():
        identificacion = session.get('identificacion')
        info_miembro = obtener_info_miembro(identificacion)
        cur = mysql.connection.cursor()
        cur.execute("""SELECT mi.*, m.*, em.FECHA_INICIO, em.FECHA_FIN
                FROM miembros AS mi
                JOIN membresia_precios AS m ON mi.ID_MEMBRESIA = m.ID_MEMBRESIA
                JOIN estado_membresia AS em ON mi.ID_MEMBRESIA = em.ID_MEMBRESIA
                WHERE mi.IDENTIFICACION  = %s;
                """, (identificacion,))  
        rows = cur.fetchall()
        cur.close()
        return render_template('cliente/miembro_estado_membresia.html', rows=rows, info_miembro=info_miembro)

# Vista para eliminar usuario
@app.route('/listado_usuarios', methods=['GET', 'POST'])
def listado_usuarios():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM miembros')
    data = cur.fetchall()
    mysql.connection.commit()
    return render_template('administrador/listado_usuarios.html', miembros=data)

# Vista para cambiar el estado de un usuario
@app.route('/estado_usuario', methods=['GET', 'POST'])
def estado_usuario():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM miembros')
    data = cur.fetchall()
    mysql.connection.commit()
    return render_template('administrador/estado_usuario.html', miembros=data)


#accion de cambiar el estado de un miembro
@app.route('/cambiar_estado_miembro', methods=['POST'])
def cambiar_estado_miembro():
    if request.method == 'POST':
        miembro_id=None
        estado_actual=None
        miembro_id = request.form.get('miembro_id')
        # Realiza una consulta para obtener el estado actual del miembro
        cur = mysql.connection.cursor()
        cur.execute("SELECT estado FROM miembros WHERE IDENTIFICACION = %s", (miembro_id,))
        estado_actual = cur.fetchone()
        print(estado_actual)
        # Cambia el estado (por ejemplo, de True a False o viceversa)
        nuevo_estado = not estado_actual[0]
        # Realiza la actualización en la base de datos
        cur.execute("UPDATE miembros SET estado = %s WHERE IDENTIFICACION = %s", (nuevo_estado, miembro_id))
        mysql.connection.commit()
        cur.close()
        flash('Estado actualizado correctamente')
    return redirect(url_for('estado_usuario') ) # Renderiza la plantilla con los datos actualizados


# Vista para editar usuario
@app.route('/editar_miembro', methods=['GET', 'POST'])
def editar_miembro():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM miembros')
    data = cur.fetchall()
    mysql.connection.commit()

    return render_template('administrador/editar_miembro.html', miembros=data)

# accion de buscar usuario
@app.route("/edit/<string:id>")
def buscarid(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM miembros WHERE IDENTIFICACION = %s', (id,))
    data = cur.fetchall()
   # mysql.connection.commit()
   # flash ('miembro editado correctamente')
    return render_template('administrador/vista_editar.html', miembro=data[0])


# accion de editar usuario
@app.route("/update/<id>", methods=['POST'])
def getid(id):
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        edad = request.form['edad']
        correo = request.form['correo']
        telefono = request.form['telefono']
        contraseña = request.form['contraseña']

    cur = mysql.connection.cursor()
    cur.execute('UPDATE miembros SET NOMBRE = %s, APELLIDO = %s, EDAD = %s, CORREO = %s, TELEFONO = %s, CONTRASENA = %s WHERE IDENTIFICACION = %s',
                (nombre, apellido, edad, correo, telefono, contraseña, id))
    mysql.connection.commit()
    flash('miembro editado correctamente')
    return redirect(url_for('editar_miembro'))


# Vista para agregar usuario
@app.route('/admin/agregar_usuario', methods=['GET', 'POST'])
def agregar_usuario():
    if request.method == 'POST':
        # Obtener los datos del formulario
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        edad = request.form['edad']
        correo = request.form['correo']
        telefono = request.form['telefono']
        contraseña = request.form['contraseña']
        estado = request.form['estado']
        identificacion = request.form['identificacion']
       
        # Agregar el usuario a la base de datos
        cur = mysql.connection.cursor()

        cur.execute('SET foreign_key_checks = 0;')

        cur.execute('INSERT INTO miembros (IDENTIFICACION, NOMBRE, APELLIDO, EDAD, CORREO, TELEFONO, CONTRASENA, ESTADO) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (identificacion, nombre, apellido, edad, correo, telefono, contraseña, estado))

        
        
        mysql.connection.commit()
        flash('Usuario agregado correctamente')

        # Redirigir a la página de administración o mostrar un mensaje de éxito
        # return redirect(url_for('administrador'))

    return render_template('administrador/agregar_usuario.html')


# Vista buscar miembro
@app.route('/buscar_miembro', methods=['GET', 'POST'])
def buscar_miembro():
    data = None
    if request.method == 'POST':
        # Obtén el término de búsqueda del formulario
        nombre = request.form.get('nombre')
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM miembros WHERE LOWER(NOMBRE) = %s", (nombre,))
        data = cur.fetchall()
        cur.close()
        if data:
            # flash('¡Miembro encontrado!.')
            return render_template('administrador/buscar_miembro.html', resultados=data)
        else:
            flash('No se encontraron miembros con esa identificación.')
    return render_template('administrador/buscar_miembro.html')


# Vista para agregar máquina
@app.route('/agregar_maquina', methods=['GET', 'POST'])
def agregar_maquina():
    if request.method == 'POST':
        nombre = request.form['nombre']
        estado = request.form['estado']
        proveedor = request.form['proveedor']
        precio = request.form['precio']
        fechaCompra = request.form['fechaCompra']
        disponibilidad = request.form['disponibilidad']

        cur = mysql.connection.cursor()

        # Verificar si el proveedor ya existe
        cur.execute('SELECT ID_PROVEEDOR FROM proveedor_maquinaria WHERE NOMBRE = %s', (proveedor,))
        resultado = cur.fetchone()

        if resultado:
            # Si el proveedor existe, obtén el ID_PROVEEDOR
            id_proveedor = resultado[0]
        else:
            # Si el proveedor no existe, inserta y obtén el ID_PROVEEDOR
            cur.execute('INSERT INTO proveedor_maquinaria (NOMBRE) VALUES (%s)', (proveedor,))
            mysql.connection.commit()
            cur.execute('SELECT LAST_INSERT_ID()')
            id_proveedor = cur.fetchone()[0]
        
        cur.execute('INSERT INTO disponibilidad_maquinaria (DISPONIBILIDAD) VALUES (%s)', (disponibilidad,))
        cur.execute('SELECT LAST_INSERT_ID()')
        id_dispo = cur.fetchone()[0]
        cur.execute('INSERT INTO estado_maquinaria (NOMBRE) VALUES (%s)', (estado,))
        cur.execute('SELECT LAST_INSERT_ID()')
        id_estado = cur.fetchone()[0]

        # Insertar en la tabla maquina
        cur.execute('SET foreign_key_checks = 0;')
        cur.execute('INSERT INTO maquina (NOMBRE, ID_ESTADO_MAQUINA, ID_DISPONIBILIDAD_MAQUINARIA) VALUES (%s, %s,%s)',
                    (nombre, id_dispo, id_estado))
        cur.execute('SELECT LAST_INSERT_ID()')
        id_maquina = cur.fetchone()[0]

        # Insertar en la tabla historial_maquinaria
        cur.execute('INSERT INTO historial_maquinaria (FECHA_COMPRA, PRECIO, ID_PROVEEDOR, ID_MAQUINA) VALUES (%s, %s, %s, %s)',
                    (fechaCompra, precio, id_proveedor, id_maquina))

        mysql.connection.commit()
        cur.close()

        flash('Máquina agregada correctamente')

    return render_template('administrador/agregar_maquina.html')


# Vista mirar el listado de maquinas
@app.route('/lista_maquinas', methods=['GET', 'POST'])
def lista_maquinas():
    data = None
    cur = mysql.connection.cursor()
    cur.execute('SELECT m.ID_MAQUINA, m.NOMBRE, m.ID_ESTADO_MAQUINA, m.ID_DISPONIBILIDAD_MAQUINARIA, em.NOMBRE AS estado_nombre, dm.DISPONIBILIDAD AS disponibilidad_nombre FROM maquina m JOIN estado_maquinaria em ON m.ID_ESTADO_MAQUINA = em.ID_ESTADO_MAQUINA JOIN disponibilidad_maquinaria dm ON m.ID_DISPONIBILIDAD_MAQUINARIA = dm.ID_DISPONIBILIDAD_MAQUINARIA')
    data = cur.fetchall()
    mysql.connection.commit()
    return render_template('administrador/lista_maquinas.html', maquinas=data)

# Vista del estado de máquinas
@app.route('/estado_maquinas', methods=['GET', 'POST'])
def estado_maquinas():
    data = None
    cur = mysql.connection.cursor()

    # Obtén los datos de la tabla maquina, incluyendo la llave foránea para estado y disponibilidad
    cur.execute('SELECT m.ID_MAQUINA, m.NOMBRE, m.ID_ESTADO_MAQUINA, m.ID_DISPONIBILIDAD_MAQUINARIA, em.NOMBRE AS estado_nombre, dm.DISPONIBILIDAD AS disponibilidad_nombre FROM maquina m JOIN estado_maquinaria em ON m.ID_ESTADO_MAQUINA = em.ID_ESTADO_MAQUINA JOIN disponibilidad_maquinaria dm ON m.ID_DISPONIBILIDAD_MAQUINARIA = dm.ID_DISPONIBILIDAD_MAQUINARIA')
    data = cur.fetchall()

    mysql.connection.commit()
    return render_template('administrador/estado_maquinas.html', maquinas=data)


# accion de editar estado de máquina
@app.route('/cambiar_estado_maquina', methods=['POST'])
def cambiar_estado():
    if request.method == 'POST':
        estado_id = request.form.get('estado_id')
        dispo_id = request.form.get('dispo_id')

        cur = mysql.connection.cursor()

        # Obtén el nombre actual del estado en estado_maquinaria
        cur.execute("SELECT NOMBRE FROM estado_maquinaria WHERE ID_ESTADO_MAQUINA = %s", (estado_id,))
        estado_actual = cur.fetchone()

        # Obtén la disponibilidad actual en disponibilidad_maquinaria
        cur.execute("SELECT DISPONIBILIDAD FROM disponibilidad_maquinaria WHERE ID_DISPONIBILIDAD_MAQUINARIA = %s", (dispo_id,))
        disponibilidad_actual = cur.fetchone()

        if estado_actual is not None and disponibilidad_actual is not None:
            # Cambia el nombre de 'Activo' a 'Inactivo' y viceversa
            nuevo_estado = 1 if estado_actual[0] == 0 else 0
            nuevo_disponibilidad = 1 - disponibilidad_actual[0]  # Cambia 0 por 1 y viceversa

            # Actualiza el nombre en estado_maquinaria
            cur.execute("UPDATE estado_maquinaria SET NOMBRE = %s WHERE ID_ESTADO_MAQUINA = %s", (nuevo_estado, estado_id))

            # Actualiza la disponibilidad en disponibilidad_maquinaria
            cur.execute("UPDATE disponibilidad_maquinaria SET DISPONIBILIDAD = %s WHERE ID_DISPONIBILIDAD_MAQUINARIA = %s", (nuevo_disponibilidad, dispo_id))

            mysql.connection.commit()
            flash('Estado actualizado correctamente')
        else:
            flash('Error: Estado o disponibilidad no encontrados')

        cur.close()
        return redirect(url_for('estado_maquinas'))  # Renderiza la plantilla con los datos actualizados

# Traer el historial de la máquina
@app.route("/historial/<id>")
def gethistorial(id):
        cur = mysql.connection.cursor()
        cur.execute("""
        SELECT historial_maquinaria.*, proveedor_maquinaria.NOMBRE AS NombreProveedor
        FROM historial_maquinaria
        LEFT JOIN proveedor_maquinaria ON historial_maquinaria.ID_PROVEEDOR = proveedor_maquinaria.ID_PROVEEDOR
        WHERE historial_maquinaria.ID_MAQUINA = %s
        """, (id,))
        data = cur.fetchall()
        cur.close()
        flash('Historial de máquina encontrado correctamente')
        return render_template('administrador/vista_historial_maquina.html', resultados=data) # Renderiza la plantilla con los datos actualizados


#vista de buscar maquina
@app.route('/buscar_maquina', methods=['GET', 'POST'])
def buscar_maquina():
    data = None
    if request.method == 'POST':
        # Obtén el término de búsqueda del formulario
        nombre = request.form.get('nombre')
        cur = mysql.connection.cursor()
        cur.execute("""SELECT m.*, d.DISPONIBILIDAD, e.NOMBRE AS ESTADO_NOMBRE
                        FROM maquina m
                        JOIN disponibilidad_maquinaria d ON m.ID_DISPONIBILIDAD_MAQUINARIA = d.ID_DISPONIBILIDAD_MAQUINARIA
                        JOIN estado_maquinaria e ON m.ID_ESTADO_MAQUINA = e.ID_ESTADO_MAQUINA
                        WHERE LOWER(m.nombre) =%s""", (nombre,))
        data = cur.fetchall()
        print(data)
        cur.close()
        if data:
            flash('Máquina encontrado.')
            return render_template('buscar_maquina.html', resultados=data)
        else:
            flash('No se encontraron máquinas con ese nombre.')
    return render_template('administrador/buscar_maquina.html')


# Vista mantenimiento de maquinas
@app.route('/mantenimiento_maquinas', methods=['GET', 'POST'])
def mantenimiento_maquinas():
    data = None
    cur = mysql.connection.cursor()
    # traer solo las maquinas que estan en mal estado
    cur.execute('''
    SELECT maquina.*, estado_maquinaria.NOMBRE AS estado_nombre
    FROM maquina
    JOIN estado_maquinaria ON maquina.ID_ESTADO_MAQUINA = estado_maquinaria.ID_ESTADO_MAQUINA
    WHERE estado_maquinaria.NOMBRE = 0
    ''')
    data = cur.fetchall()
    mysql.connection.commit()
    return render_template('administrador/mantenimiento_maquinas.html', miembros=data)

# agendar cita mantenimiento
@app.route("/mantenimiento/<maquina_id>", methods=['GET', 'POST'])
def getmantenimiento(maquina_id):
    cur = mysql.connection.cursor()
    cur.execute('SET foreign_key_checks = 0;')
    cur.execute("SELECT * FROM maquina WHERE ID_MAQUINA = %s", (maquina_id,))
    maquina = cur.fetchone()
    cur.close()

    if request.method == 'POST':
        fecha = request.form.get('fecha')
        hora = request.form.get('hora')
        observacion = request.form.get('observacion')

        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO proceso_citas (TIPO_ESTADO) VALUES (%s)", (str('En proceso'),))
        cur.execute("SELECT LAST_INSERT_ID()")
        last_inserted_id = cur.fetchone()[0]

        # Insertar la cita de mantenimiento en la tabla citas_mantenimiento
        cur.execute("INSERT INTO citas_mantenimiento (ID_MAQUINA, FECHA_CITA, HORA, OBSERVACION, ID_ESTADO_CITA) VALUES (%s, %s, %s, %s, %s)",
                    (maquina_id, fecha, hora, observacion, last_inserted_id))


        mysql.connection.commit()
        cur.close()

        flash(f'Cita agendada para {fecha} a las {hora}')

    return render_template('administrador/vista_mantenimiento.html', maquina=maquina)

# Vista listado instructores administrador
@app.route('/listado_instructores', methods=['GET', 'POST'])
def listado_instructores():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM empleado WHERE ID_SALARIO_EMPLE = '2'")
    data = cur.fetchall()
    mysql.connection.commit()
    
    return render_template('administrador/listado_instructores.html', empleado=data)

# Agregar instructor
@app.route('/agregar_instructor', methods=['GET', 'POST'])
def agregar_instructor():
    if request.method == 'POST':
        print(request.form)
        # Obtener los datos del formulario
        id_salario_emple = 2
        estado = 1
        cedula = request.form['cedula']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        genero = request.form['genero']
        edad = request.form['edad']
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        horario = request.form.get('horario')

        # Obtener las especialidades y unirlas como una cadena
        especialidad = ', '.join(request.form.getlist('especialidad'))

        # Agregar el usuario a la base de datos utilizando parámetros
        cur = mysql.connection.cursor()
        cur.execute('INSERT INTO empleado (IDENTIFICACION_EMPLEADO, NOMBRE, APELLIDO, CONTRASENA, EDAD, CORREO, GENERO, ID_SALARIO_EMPLE, ESPECIALIDAD, HORARIO, ESTADO) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (cedula, nombre, apellido, contrasena, edad, correo, genero, id_salario_emple, especialidad, horario, estado))
        
        mysql.connection.commit()
        flash('Instructor agregado correctamente')

    return render_template('administrador/agregar_instructor.html')

# Vista editar instructor
@app.route('/editar_instructor', methods=['GET', 'POST'])
def editar_instructor():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM empleado WHERE ID_SALARIO_EMPLE = "2"')
    data = cur.fetchall()
    mysql.connection.commit()

    return render_template('administrador/editar_instructor.html', empleado=data)

# Accion editar instructor
@app.route('/vista_editar_instructor/<cedula>', methods=['GET', 'POST'])
def vista_editar_instructor(cedula):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM empleado WHERE IDENTIFICACION_EMPLEADO = %s', (cedula,))
    instructor = cur.fetchone()
    mysql.connection.commit()

    if instructor:
        if request.method == 'POST':
            # Lógica para actualizar los detalles del instructor en la base de datos
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            edad = request.form['edad']
            correo = request.form['correo']
            horario = request.form.get('horario')
            especialidad = ', '.join(request.form.getlist('especialidad'))

            # Lista de tuplas
            campos_actualizar = []

            # Verificar y agregar campos al actualizar
            if nombre:
                campos_actualizar.append(('nombre', nombre))
            if apellido:
                campos_actualizar.append(('apellido', apellido))
            if edad:
                campos_actualizar.append(('edad', edad))
            if correo:
                campos_actualizar.append(('correo', correo))
            if horario:
                campos_actualizar.append(('horario', horario))
            if especialidad:
                campos_actualizar.append(('especialidad', especialidad))

            # Verifica si hay campos para actualizar
            if campos_actualizar:

                consulta = 'UPDATE empleado SET ' + ', '.join([f'{campo} = %s' for campo, valor in campos_actualizar]) + f' WHERE IDENTIFICACION_EMPLEADO = %s' 
                
                # Valores que se actualizarán
                valores_actualizar = [valor for campo, valor in campos_actualizar] + [cedula]

                cur.execute(consulta, valores_actualizar)
                mysql.connection.commit()

                flash('Instructor editado correctamente')
                return redirect(url_for('editar_instructor'))
            else:
                flash('Edición sin cambios')

        return render_template('administrador/vista_editar_instructor.html')

# Buscar instructor
@app.route('/buscar_instructor', methods=['GET', 'POST'])
def buscar_instructor():
    data = None
    if request.method == 'POST':
        # Obtén el término de búsqueda del formulario
        cedula = request.form.get('cedula')
        id_salario_emple = 2
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM empleado WHERE IDENTIFICACION_EMPLEADO = %s AND ID_SALARIO_EMPLE = %s", (cedula,id_salario_emple))
        data = cur.fetchall()
        cur.close()
        if data:
            flash('Instructor encontrado.')
            return render_template('administrador/buscar_instructor.html', resultados=data)
        else:
            flash('No se encontraron instructores con esa identificación.')
    return render_template('administrador/buscar_instructor.html')

# Vista estado instructor
@app.route('/estado_instructor', methods=['GET', 'POST'])
def estado_instructor():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM empleado WHERE ID_SALARIO_EMPLE = 2')
    data = cur.fetchall()
    mysql.connection.commit()
    return render_template('administrador/estado_instructor.html', empleado=data)


# Acción cambiar estado instructor
@app.route('/cambiar_estado_instructor', methods=['POST'])
def cambiar_estado_instructor():
    if request.method == 'POST':
        cedula = request.form.get('cedula')
        
        # Realiza una consulta para obtener el estado actual del instructor
        cur = mysql.connection.cursor()
        cur.execute("SELECT estado FROM empleado WHERE IDENTIFICACION_EMPLEADO = %s", (cedula,))
        estado_actual = cur.fetchone() 
        # Cambia el estado (por ejemplo, de True a False o viceversa)
        nuevo_estado = not estado_actual[0]
        # Realiza la actualización en la base de datos
        cur.execute("UPDATE empleado SET estado = %s WHERE IDENTIFICACION_EMPLEADO = %s", (nuevo_estado, cedula))
        mysql.connection.commit()
        cur.close()
        flash('Estado actualizado correctamente')
    return redirect(url_for('estado_instructor') )

# Nomina Instructores
@app.route('/gestion_nomina', methods=['GET', 'POST'])
def gestion_nomina():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM empleado WHERE ID_SALARIO_EMPLE = "2"')
    data = cur.fetchall()
    mysql.connection.commit()

    return render_template('administrador/gestion_nomina.html', empleado=data)

def generar_pdf(cedula, nombre, apellido):
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    id_salario_emple = 2
    
    cur = mysql.connection.cursor()
    cur.execute('SELECT SALARIO FROM salario_empleado WHERE ID_SALARIO_EMPLE = %s', (id_salario_emple,))
    data = cur.fetchone()

    salario_base = data[0]
    mysql.connection.commit()
    aporte_salud = 4 * salario_base / 100
    aporte_pension = 4 * salario_base / 100
    aux_transporte = 140606
    total_devengos = aux_transporte + salario_base
    total_deducciones = aporte_salud + aporte_pension
    total_liquido = total_devengos - total_deducciones
   
    
    # Crear el nombre del archivo con la fecha actual
    nombre_archivo = f"recibo_nomina_{fecha_actual}.pdf"
    
    # Crear un documento PDF con un título específico
    doc = SimpleDocTemplate(nombre_archivo, pagesize=letter, title="Recibo de Nómina")

    # Crear datos para la tabla basados en la estructura proporcionada
    datos = [
        ["EMPRESA", "", ""],
        ["Nombre de la Empresa:", "Gimnasio La Candelaria", ""],
        ["Dirección:", "Cl. 68 Sur # 47 - 10, Cdad. Bolívar, Bogotá", ""],
        ["", "", ""],
        ["TRABAJADOR/A", "", ""],
        ["Nombre del Instructor:", f"{nombre} {apellido}", ""],
        ["Identificación:", cedula, ""],
        ["", "", ""], 
        ["Devengos", "Cantidad", "Precio ($)", "Total ($)"],
        ["Salario base", "30 días", 48910, int(salario_base)],
        ["Auxilio de transporte", "", int(aux_transporte), int(aux_transporte)],
        ["", "", "Total", int(total_devengos)],
        ["Deducciones", "Cantidad", "Precio ($)", "Total ($)"],
        ["Aporte a la salud", "", "4%", int(aporte_salud)],
        ["Aporte a la pensión", "", "4%", int(aporte_pension)],
        ["", "", "Total", int(total_deducciones)],
        ["", "", ""],
        ["Liquido a percibir", int(total_liquido), ""],
        ["Fecha generación de nomina", fecha_actual, "", ""],
    ]

    # Crear la tabla y darle estilo con bordes
    tabla = Table(datos, colWidths=(200, 100, 100, 100))
    estilo_tabla = TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (3, 0), colors.Color(0.8, 0.8, 0.8)),
        ('BACKGROUND', (0, 4), (3, 4), colors.Color(0.8, 0.8, 0.8)),
        ('BACKGROUND', (0, 8), (3, 8), colors.Color(1.0, 1.0, 0.6)),
        ('BACKGROUND', (0, 12), (3, 12), colors.Color(1.0, 1.0, 0.6)),
        ('BACKGROUND', (1, 17), (3, 17), colors.Color(0.8, 0.8, 1.0))
    ])
    
    # Ajustar la combinación de filas
    estilo_tabla.add('SPAN', (0, 0), (3, 0))  # Combinar la primera fila
    # Ajustar la alineación de la primera fila
    estilo_tabla.add('ALIGN', (0, 0), (3, 0), 'CENTER')
    estilo_tabla.add('SPAN', (0, 4), (3, 4))
    estilo_tabla.add('ALIGN', (0, 4), (3, 4), 'CENTER')
    estilo_tabla.add('SPAN', (1, 1), (3, 1))
    estilo_tabla.add('SPAN', (1, 2), (3, 2))
    estilo_tabla.add('SPAN', (1, 5), (3, 5))
    estilo_tabla.add('SPAN', (1, 6), (3, 6))
    estilo_tabla.add('SPAN', (0, 3), (3, 3))
    estilo_tabla.add('SPAN', (0, 7), (3, 7))
    estilo_tabla.add('SPAN', (0, 11), (1, 11))
    estilo_tabla.add('SPAN', (0, 15), (1, 15))
    estilo_tabla.add('SPAN', (1, 17), (3, 17))
    estilo_tabla.add('SPAN', (1, 18), (3, 18))

    # Aplicar el estilo a la tabla
    tabla.setStyle(estilo_tabla)

    # Construir la tabla y agregarla al documento
    elementos = []
    elementos.append(tabla)

    # Construir el PDF
    doc.build(elementos)

    return nombre_archivo

@app.route('/descargar_pdf/<cedula>/<nombre>/<apellido>')
def descargar_pdf(cedula, nombre, apellido):
    nombre_archivo = generar_pdf(cedula, nombre, apellido)

    # Configurar las cabeceras HTTP para indicar el nombre del archivo al navegador
    return send_file(nombre_archivo, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=4000)
