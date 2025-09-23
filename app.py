from flask import Flask, render_template, request, redirect, url_for, flash, session

from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

def generar_token(email):
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta (hours=1)
    cur = mysql.connection.cursor()
    cur.execute("UPDATE usuarios SET reset_token= %s, token_expiry = %s WHERE username = %s", (token, expiry,email))
    mysql.connection.commit()
    cur.close()
    return token

def enviar_correo_reset(email,token):
    enlace = url_for('reset', token = token,_external=True)
    cuerpo = f"""Hola, Solicitaste recuperar tu contraseña. Haz click en el siguiente enlace:
    {enlace}
    Este enlace expirará en 1 hora.
    Si no lo solicitaste, ignora este mensaje. """
    
    remitente = 'yanfristib@gmail.com'
    clave = 'jkud ywjs kvnk thia'
    mensaje = MIMEText(cuerpo)
    mensaje['subject'] = 'Recuperar contraseña'
    mensaje['From'] = 'yanfristib@gmail.com'
    mensaje['To'] = email

    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    server.login(remitente,clave)
    server.sendmail(remitente,email,mensaje.as_string())
    server.quit()


app = Flask(__name__)
app.secret_key = 'clave_secreta'
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='airsoft'

mysql =MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method =='POST':
        username = request.form['username']
        password_ingresada = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("""
        SELECT u.idUsuario, u.nombre, u.password, r.nombreRol
        FROM usuarios u
        JOIN usuario_rol ur ON u.idUsuario= ur.idUsuario
        JOIN roles r ON ur.idRol = r.idRol
        WHERE u.username =%s
        """, (username,))
        
        usuario = cur.fetchone()
        

        if usuario and check_password_hash (usuario [2], password_ingresada):
           session ['usuario'] = usuario[1]
           session ['rol'] = usuario[3]
           flash (f" | Bienvenido {usuario [1]}!")

           cur.execute("""
            INSERT INTO registro_login (idUsuario, fecha)
            VALUES (%s, NOW())
            """,(usuario[0],))
           mysql.connection.commit()

           cur.close()

           if usuario[3] == 'Admin':
              return redirect(url_for('dashboard'))
           elif usuario[3] == 'Usuario':
               return redirect(url_for('catalogo'))
           else:
               flash("Rol no reconocido")
               return redirect(url_for('login'))
        else:
           flash("Usuario o contraseña incorrecta")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada correctamente")
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form ['nombre']
        apellido = request.form ['apellido']
        username = request.form ['username']
        password = request.form ['password']
        hash = generate_password_hash (password)


        cur = mysql.connection.cursor ()
        try: 
            cur.execute("""INSERT INTO usuarios(nombre, apellido, username, password) VALUES (%s, %s, %s, %s) 
                        """, (nombre, apellido, username, hash))
            mysql.connection.commit()
            
            cur.execute("SELECT idUsuario FROM usuarios WHERE username =%s", (username,))
            nuevo_usuario = cur.fetchone()
            
            cur.execute("INSERT INTO usuario_rol(idUsuario, idRol) VALUES (%s, %s)", (nuevo_usuario[0], 2))
            mysql.connection.commit()
            flash ("Usuario registrado con exito")            
            return redirect(url_for('login'))
        except:
            flash("Este correo ya esta registrado")
        finally:
            cur.close()        



    return render_template('registro.html')

@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method =='POST':
       email = request.form['email']
       
       cur = mysql.connection.cursor()
       cur.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (email,))
       existe = cur.fetchone()
       cur.close()

       if not existe:
           flash("Este correo no está registrado.")
           return redirect(url_for('forgot'))


       token = generar_token(email)
       enviar_correo_reset(email, token) 

       flash ("Te enviamos un correo con el enlace para restablecer tu contraseña")
       return redirect(url_for('login'))
    return render_template('forgot.html')
    
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset (token):
    cur = mysql.connection.cursor()
    cur.execute("SELECT idUsuario, token_expiry FROM usuarios WHERE reset_token = %s", (token,))
    usuario = cur.fetchone()
    cur.close()

    if not usuario or datetime.now() >usuario [1]:
       flash ("Token inválido o expirado.")
       return redirect(url_for('forgot'))
    if request.method == 'POST':
        nuevo_password = request.form ['password']
        hash_nueva = generate_password_hash (nuevo_password)

        cur = mysql.connection.cursor()
        cur.execute("UPDATE  usuarios SET password=%s, reset_token=NULL, token_expiry=NULL WHERE idUsuario=%s", (hash_nueva, usuario[0]))
        mysql.connection.commit()
        cur.close()

        flash ("Tu contraseña ha sido actualizada.")
        return redirect(url_for('login'))
    return render_template('reset.html')



@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash("Debes iniciar sesión para acceder al dashboard.")
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
         SELECT u.idUsuario, u.nombre, u.apellido, u.username, r.nombreRol, ur.idRol
         FROM usuarios u
         LEFT JOIN usuario_rol ur ON u.idUsuario = ur.idUsuario
         LEFT JOIN roles r ON ur.idRol = r.idRol          
         """)
    usuarios = cursor.fetchall()
    cursor.close()
    return render_template('dashboard.html', usuarios=usuarios)


@app.route('/actualizar/<int:id>', methods=['POST'])
def actualizar (id):
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    correo = request.form['correo']
    rol = request.form['rol']


    cursor = mysql.connection.cursor()
    cursor.execute("""UPDATE usuarios SET nombre=%s,apellido =%s, username=%s WHERE idUsuario=%s """,(nombre,apellido,correo,id))
    cursor.execute("SELECT * FROM usuario_rol WHERE idUsuario =%s", (id,))
    existe = cursor.fetchone()
    
    if existe:
        cursor.execute("UPDATE usuario_rol SET idRol =%s WHERE idUsuario=%s", (rol,id))
    else:
        cursor.execute("INSERT INTO usuario_rol(idUsuario, idRol) VALUES (%s, %s)", (id,rol))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('dashboard'))

@app.route('/eliminar/<int:id>')
def eliminar(id):
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM usuarios WHERE idUsuario=%s',(id,))
    mysql.connection.commit()
    cursor.close()
    flash ('Usuario eliminado')
    return redirect(url_for('dashboard'))

@app.route('/inventario')
def inventario():
    if 'rol' not in session or session['rol'] != 'Admin':
       flash("Acceso restringido solo para los administradores")
       return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    return render_template('inventario.html', productos=productos)    

@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if 'rol' not in session or session['rol'] !='Admin':
        flash("Acceso restringido solo para los administradores")
        return redirect(url_for('login'))
    if request.method =='POST':
       nombre =request.form['nombre']
       descripcion =request.form['descripcion']
       precio =request.form['precio']
       cantidad =request.form['cantidad']
       imagen =request.files['imagen']
       
       filename  = secure_filename(imagen.filename)
       imagen.save(os.path.join('static/uploads', filename))
       cursor = mysql.connection.cursor()
       cursor.execute("""
          INSERT INTO productos (nombre_producto, descripcion, precio, cantidad, imagen)
          VALUES (%s, %s, %s, %s, %s)
       """, (nombre, descripcion, precio, cantidad, filename))
       mysql.connection.commit()
       cursor.close()
       
       flash("Producto agregado correctamente")
       return redirect(url_for('inventario'))
    return render_template('agregar_producto.html')


@app.route('/catalogo')
def catalogo():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    return render_template("catalogo.html", productos=productos)

@app.route('/agregar', methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        nombre = request.form['nombre']
        precio = request.form['precio']
        imagen = request.files['imagen']

        if imagen:
            filename = secure_filename(imagen.filename)
            path_imagen = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(path_imagen)
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("INSERT INTO producto (nombre_producto, precio, imagen) VALUES (%s, %s, %s)",
                           (nombre, precio, filename))
            db.commit()
            flash("Producto agregado con éxito")
            return redirect(url_for('index'))

    return render_template("agregar.html")


@app.route('/agregar2', methods=["GET", "POST"])
def productos():
    if request.method == "POST":
        nombre = request.form['nombre']
        precio = request.form['precio']
        descripcion=request.form['descripcion']
        cantidad = request.form['cantidad']
        imagen = request.files['imagen']
        categoria = request.form['categoria']
        proveedor = request.form['proveedor']
        if imagen:
            filename = secure_filename(imagen.filename)
            path_imagen = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(path_imagen)
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("INSERT INTO producto (nombre_producto, descripcion, precio,cantidad,imagen,id_categoria,id_proveedor) VALUES (%s, %s, %s,%s,%s,%s,%s)",
                           (nombre, precio, descripcion, cantidad,filename,categoria,proveedor))
            cursor.commit()
            flash("Producto agregado con éxito")
            return redirect(url_for('productos'))

    return render_template("productos.html")

@app.route('/carrito/<int:id>')
def carrito(id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos WHERE idProducto=%s", (id,))
    producto = cursor.fetchone()

    if "carrito" not in session:
        session['carrito'] = []

    session['carrito'].append(producto)
    session.modified = True

    return redirect(url_for('mostrar_carrito'))


@app.route('/mostrar_carrito')
def mostrar_carrito():
    carrito = session.get("carrito", [])
    total = sum([float(p['precio']) for p in carrito])
    return render_template("carrito.html", carrito=carrito, total=total)

@app.route('/factura')
def factura():
    carrito = session.get("carrito", [])
    total = sum([float(p['precio']) for p in carrito])
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    session.pop("carrito", None)
    return render_template("factura.html", carrito=carrito, total=total)




if __name__ =='__main__':
    app.run(port=5000,debug=True)
    
