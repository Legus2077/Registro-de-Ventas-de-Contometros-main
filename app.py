
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyodbc
import webbrowser
import threading
import time
import decimal

app = Flask(__name__)
app.secret_key = 'clave_super_secreta'

navegador_abierto = False

def abrir_navegador():
    global navegador_abierto
    if not navegador_abierto:
        time.sleep(1)
        webbrowser.open("http://127.0.0.1:5000/")
        navegador_abierto = True

def conectar_bd():
    conexion = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-JEQJ9JP;'    
        'DATABASE=GestorVentas;'
        'Trusted_Connection=yes;'
    )
    return conexion

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Usuario WHERE username = ? AND password = ?", (username, password))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Usuario o contraseña incorrectos'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

#----------------------------DASHBOARD-------------------------------
#----------------------------------------------------------------------
@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()
    

    cursor.execute("SELECT ISNULL(SUM(monto), 0) FROM Ventas")

    total_ganancia = float(cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM Ventas")
    total_ventas = int(cursor.fetchone()[0])

    cursor.execute("""
        SELECT 
            YEAR(fecha) AS anio,
            MONTH(fecha) AS mes,
            SUM(monto) AS ganancia_mensual
        FROM Ventas
        GROUP BY YEAR(fecha), MONTH(fecha)
        ORDER BY anio, mes
    """)
    ganancia_mensual_raw = cursor.fetchall()
    
    conn.close() 
    
    ganancia_mensual = []
    
    if ganancia_mensual_raw:
        for row in ganancia_mensual_raw:

            monto_seguro = float(row[2])
            
            ganancia_mensual.append((int(row[0]), int(row[1]), monto_seguro))

    return render_template('dashboard.html',
                           usuario=session['usuario'],
                           total_ganancia=total_ganancia,
                           total_ventas=total_ventas,
                           ganancia_mensual=ganancia_mensual) 

#----------------------------------------------------------------------
#-----------------------------registrar venta---------------------------

@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    mensaje = None
    error = None

    if request.method == 'POST':
        try:
            descripcion = request.form['descripcion']
            cliente = request.form['cliente']
            dni = request.form['dni']
         
            monto = float(request.form['monto'])
            fecha = request.form['fecha']

            conn = conectar_bd()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Ventas (descripcion, cliente, dni, monto, fecha) VALUES (?, ?, ?, ?, ?)",
                           (descripcion, cliente, dni, monto, fecha))
            conn.commit()
            conn.close()
            
            return redirect(url_for('dashboard', mensaje='Venta registrada correctamente.'))

        except Exception as e:
            error = f'Error al registrar venta: {e}'
            if 'conn' in locals() and conn:
                conn.close()
            
    return render_template('registrar_venta.html', 
                           usuario=session['usuario'], 
                           mensaje=mensaje, 
                           error=error)

#----------------------------ver_ventas-------------------------------
#----------------------------------------------------------------------
@app.route('/ver_ventas', methods=['GET', 'POST'])
def ver_ventas():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = conectar_bd()
    cursor = conn.cursor()
    
    mensaje = None
    error = None
    
    ventas = []
    total = 0
    cliente_nombre = None
    cliente_dni = None
    venta_editar = None 
    
    busqueda = request.args.get('busqueda', request.form.get('busqueda', ''))
    anio = request.args.get('anio', type=int)
    mes = request.args.get('mes', type=int)
    editar_id = request.args.get('editar', type=int)

    if request.method == 'POST':
        
        if 'eliminar' in request.form:
            try:
                venta_id = int(request.form['eliminar'])
                cursor.execute("DELETE FROM Ventas WHERE id = ?", (venta_id,))
                conn.commit()
                mensaje = 'Venta eliminada correctamente.'
               
                return redirect(url_for('ver_ventas', mensaje=mensaje, busqueda=busqueda, anio=anio, mes=mes))
            except Exception as e:
                error = f'Error al eliminar venta: {e}'

        elif 'editar' in request.form:
            try:
                venta_id = int(request.form['venta_id'])
                descripcion = request.form['descripcion']
                cliente = request.form['cliente']
                dni = request.form['dni']
                monto = float(request.form['monto'])
                fecha = request.form['fecha']
                
                cursor.execute("""
                    UPDATE Ventas SET descripcion=?, cliente=?, dni=?, monto=?, fecha=?
                    WHERE id=?
                """, (descripcion, cliente, dni, monto, fecha, venta_id))
                
                conn.commit()
                mensaje = 'Venta actualizada correctamente.'
                
                return redirect(url_for('ver_ventas', mensaje=mensaje, busqueda=busqueda, anio=anio, mes=mes))
            except Exception as e:
                error = f'Error al actualizar venta: {e}'

    query = "SELECT id, descripcion, cliente, dni, monto, CONVERT(VARCHAR(10), fecha, 23) FROM Ventas WHERE 1=1 "
    params = []
    
   
    if busqueda:
        query += " AND (dni LIKE ? OR cliente LIKE ?) "
        params.extend([f'%{busqueda}%', f'%{busqueda}%'])
        
        if busqueda.isdigit() and len(busqueda) <= 8:
             cursor.execute("SELECT TOP 1 cliente, dni FROM Ventas WHERE dni = ?", (busqueda,))
             cliente_data = cursor.fetchone()
             if cliente_data:
                cliente_nombre = cliente_data[0]
                cliente_dni = cliente_data[1]


    if anio:
        query += " AND YEAR(fecha) = ? "
        params.append(anio)
        

    if mes:
        query += " AND MONTH(fecha) = ? "
        params.append(mes)

    query += " ORDER BY fecha DESC"
   
    cursor.execute(query, params)
    ventas = cursor.fetchall()

    
    if ventas:
        
        total = sum(float(v[4]) for v in ventas) 
    
    if editar_id:
        cursor.execute("SELECT id, descripcion, cliente, dni, monto, CONVERT(VARCHAR(10), fecha, 23) FROM Ventas WHERE id = ?", (editar_id,))
        venta_editar = cursor.fetchone()


    conn.close()

   
    return render_template('ver_ventas.html',
                           usuario=session['usuario'],
                           ventas=ventas,
                           total=total,
                           busqueda=busqueda,
                           anio=anio,
                           mes=mes,
                           cliente_nombre=cliente_nombre,
                           cliente_dni=cliente_dni,
                           venta_editar=venta_editar,
                           mensaje=mensaje,
                           error=error)

#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------
@app.route('/ranking_clientes', methods=['GET'])
def ranking_clientes():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    
    desde = request.args.get('desde')  
    hasta = request.args.get('hasta')  
    top = request.args.get('top', type=int) or 20

    conn = conectar_bd()
    cursor = conn.cursor()

    query = """
        SELECT
            COALESCE(NULLIF(dni,''), cliente) AS clave_cliente,
            MAX(cliente)                           AS cliente,
            MAX(NULLIF(dni,''))                    AS dni,
            COUNT(*)                               AS compras,
            SUM(monto)                             AS total,
            MIN(fecha)                             AS primera_compra,
            MAX(fecha)                             AS ultima_compra
        FROM Ventas
        WHERE 1=1
    """
    params = []

    if desde:
        query += " AND fecha >= ?"
        params.append(desde)
    if hasta:
        query += " AND fecha <= ?"
        params.append(hasta)

    query += """
        GROUP BY COALESCE(NULLIF(dni,''), cliente)
        ORDER BY total DESC
    """

    cursor.execute(query, params)
    ranking = cursor.fetchall()
    conn.close()

    # Aplica Top N en Python para evitar lío con TOP(@var)
    ranking = ranking[:top] if ranking else []

    return render_template(
        'ranking_clientes.html',
        ranking=ranking,
        desde=desde,
        hasta=hasta,
        top=top
    )
#--------------------------------------------------------------------------------
#--------------------------------------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=abrir_navegador, daemon=True).start()
    app.run(debug=True, use_reloader=False)
