#%% Librerías
import serial
import serial.tools.list_ports
import time
import numpy as np
import scipy.stats as stats
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, filedialog
from uncertainties import ufloat, unumpy
import matplotlib.pyplot as plt
import os
import chardet
#%% Funciones
def obtener_nombre_archivo(prefijo):
    """Genera un nombre de archivo único basado en la fecha y hora actual."""
    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefijo}_{fecha_hora}.txt"
#%% Medir Intensidad c/Arduino
def medir_intensidad(comando, barra_progreso=None, ventana=None):
    """Mide la intensidad del sensor (I0 o I) según el comando dado y devuelve el promedio de 10 mediciones."""
    mediciones = []  # Lista para almacenar las mediciones individuales

    for i in range(10):  # Realizar 10 mediciones
        ser.write(comando.encode())  # Enviar comando a Arduino
        try:
            while True:
                linea = ser.readline().decode("utf-8").strip()
                if not linea:
                    continue  # Ignora líneas vacías
                if linea == "Procesando...":
                    print(linea, end="\r", flush=True)
                    continue  # Sigue esperando el dato real
                try:
                    I = float(linea)
                    mediciones.append(I)  # Agregar la medición a la lista
                    break  # Salir del bucle interno después de obtener una medición válida
                except ValueError:
                    print(f"Error al convertir datos: {linea}")
                    return None
        except Exception as e:
            print(f"Error en la medición: {e}")
            return None

        # Actualizar la barra de progreso
        if barra_progreso and ventana:
            barra_progreso['value'] = (i + 1) * 10  # Avanzar en 10% por cada medición
            ventana.update_idletasks()  # Actualizar la interfaz gráfica

    # Calcular el promedio de las 10 mediciones
    if mediciones:
        promedio_I = round(sum(mediciones) / len(mediciones), 2)
        return promedio_I
    else:
        return None  # Si no se obtuvieron mediciones válidas
#%% Usar Calibracion existente
def usar_calibracion():
    """Permite al usuario seleccionar un archivo de calibración y cargar los valores de slope e intercept."""
    global I0,slope, intercept  # Declarar slope e intercept como globales
    print('-' * 50, '\nUso calibracion existente')
    
    # Abrir un diálogo para seleccionar un archivo .txt
    archivo_calibracion = filedialog.askopenfilename()
    if not archivo_calibracion:
        messagebox.showwarning("Advertencia", "No se seleccionó ningún archivo.")
        return
    try:
        # Detectar la codificación del archivo
        with open(archivo_calibracion, 'rb') as f:
            codificacion = chardet.detect(f.read())['encoding']
        try:
            # Leer el archivo con la codificación detectada
            with open(archivo_calibracion, "r", encoding=codificacion) as archivo:
                lineas = archivo.readlines()
                
                # Buscar las líneas que contienen "Pendiente", "Ordenada" y "Fondo"
                for linea in lineas:
                    if "Pendiente:" in linea:
                        slope_str = linea.split(":")[1].strip()  # Extraer el valor de la pendiente
                        slope = float(slope_str.split("+/-")[0].strip())  # Obtener el valor numérico
                    elif "Ordenada:" in linea:
                        intercept_str = linea.split(":")[1].strip()  # Extraer el valor de la ordenada
                        intercept = float(intercept_str.split("+/-")[0].strip())  # Obtener el valor numérico
                    elif "Fondo:" in linea:
                        fondo_str = linea.split(":")[1].strip()  # Extraer el valor del fondo
                        I0 = float(fondo_str)  # Obtener el valor numérico
                
                # Verificar si todos los valores necesarios se cargaron correctamente
                if (I0 is not None) and (slope is not None) and (intercept is not None):
                    barra_progreso['value'] = 100
                    print(f"Valores cargados:\nFondo: {I0} cnts\nPendiente: {slope}\nOrdenada: {intercept}")
                    messagebox.showinfo("Uso calibración previa", f"Valores cargados:\nFondo: {I0} cnts\nPendiente: {slope}\nOrdenada: {intercept}")
                    boton_medir.config(state="normal")
                else:
                    messagebox.showerror("Error", "El archivo no contiene todos los valores necesarios.")
        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo: {e}")
    
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer el archivo: {e}")
#%%Calibrar
def calibrar(barra_progreso, ventana):
    """Realiza la calibración midiendo intensidades de soluciones conocidas.
    Se ingresa la concentracion de la solucion madre y luego se miden las concentraciones de las diluciones: [1/500, 1/250, 1/200, 1/125, 1/100, 1/80] (3 veces c/u)
    A partir de estos datos se calibra la recta Concentracion/Absorbancia
    """
    print('-'*50,'\nCalibracion iniciada')
    global I0, slope, intercept  # Declarar I0, slope e intercept como globales    
    try:
        conc_madre = simpledialog.askfloat("Concentración madre", "Ingrese la concentración madre (mg/ml):")# Solicitar la concentración madre
        if conc_madre is None:  # Si el usuario cancela
            return None, None
        
        diluciones = [500, 250, 200, 125, 100, 80]
        concentraciones = [conc_madre / d for d in diluciones]
        
        # Medir el fondo (I0)
        messagebox.showinfo("Medir fondo", "Coloque la cubeta con agua y presione OK para medir el fondo")
        
        I0 = medir_intensidad("medir", barra_progreso_3, ventana)
        if I0 is None:
            messagebox.showerror("Error", "Error en la medición del fondo.")
            barra_progreso_3['value']=0
            return None, None
        print(f'I0 = {I0}')     
        messagebox.showinfo("Información", f"I0 = {I0:.2f}")
        barra_progreso['value'] = 0
        barra_progreso_3['value']=0
        ventana.update_idletasks()
        valores_I,errores_I = [],[]
        for i, dil in enumerate(diluciones):
            MS=messagebox.askokcancel(f"Medir dilución 1/{dil}", f"Coloque la solución de dilución 1/{diluciones[i]} y presione OK...")
            if not MS:
                barra_progreso['value'] = 0
                ventana.update_idletasks()
                return None
            
            mediciones = []
            print('-'*30,f'\nDilucion = 1/{dil}')
            for _ in range(3):
                I = medir_intensidad("medir", barra_progreso_3, ventana)
                if I is not None:
                    mediciones.append(I)
                    print(f'I = {I}')
                    messagebox.showinfo(f"Dilución 1/{dil}", f"Medición {_+1}/3: I = {I:.2f}")
                    # Actualizar la barra de progreso
                    barra_progreso['value'] += (1 / 18) * 100  # Avanzar en 1/18 (3 medidas x 6 diluciones)
                    barra_progreso_3['value']=0
                    ventana.update_idletasks()  # Actualizar la interfaz gráfica
            
            if len(mediciones) == 3:
                promedio_I = np.mean(mediciones)
                valores_I.append(promedio_I)
                print(f'A = {-np.log10(promedio_I/I0)}')
                #err_I = np.std(mediciones)
                #errores_I.append(err_I)
                #messagebox.showinfo("Promedio", f"Promedio para la dilución 1/{diluciones[i]}: {ufloat(promedio_I,err_I):.2f}")
        
        absorbancias = [-np.log10(I / I0) for I in valores_I]
        
        resultado = stats.linregress(concentraciones, absorbancias)
        slope,slope_err=resultado.slope,resultado.stderr
        intercept,intercept_err=resultado.intercept,resultado.intercept_stderr
        pendiente=ufloat(slope,slope_err)
        ordenada=ufloat(intercept,intercept_err)
        messagebox.showinfo("Calibración completada", f"Ajuste de calibración: y = {slope:.2f}x + {intercept:.2f}, R² = {resultado.rvalue**2:.2f}")
        
        #fechas y directorios para el salvado
        output_date=datetime.now().strftime("%y%m%d_%H%M%S")
        output_dir= os.path.join(os.getcwd(),f'calibracion_{output_date}')
        if not os.path.exists(output_dir): # Crear el subdirectorio si no existe
            os.makedirs(output_dir)
        
        #Plot
        x=np.linspace(concentraciones[0],concentraciones[-1],1000)
        y=x*slope+intercept
        fig, ax=plt.subplots(constrained_layout=True)
        ax.plot(x,y)
        ax.text(1/4,3/4,f'C$_0$={conc_madre:1} g/L',transform=ax.transAxes,fontsize=14,ha='center',bbox=dict(alpha=0.8))
        ax.scatter(concentraciones,absorbancias)
        ax.grid()
        ax.set_xlabel('Concentracion (g/L)')
        ax.set_ylabel('Absorbancia (u.a.)')        
        plt.savefig(os.path.join(output_dir,'calibracion_'+output_date+'.png'),dpi=300)
        plt.show()
        
        #salvo tabla
        with open(os.path.join(output_dir,'calibracion_'+output_date+'.txt'), "w") as archivo:
            archivo.write(f"# Calibracion realizada el {output_date}\n")
            archivo.write("Concentracion (mg/ml), Absorbancia\n")
            for c, A in zip(concentraciones, absorbancias):
                archivo.write(f"{c:.3e}, {A:.3e}\n")
            archivo.write(f"\nFondo: {I0:.3f}\nPendiente: {pendiente:.3f}\nOrdenada: {ordenada:.3f}\nR² = {resultado.rvalue**2:.2f}\n")
        
        messagebox.showinfo("Guardado", f"Datos guardados en {output_dir}")
        if (I0 is not None) and (slope is not None) or (intercept is not None):
            boton_medir.config(state="active")  # Habilitar el botón Medir muestra después de calibrar
            #boton_medir_I0.config(state="disabled")
        
        return I0,slope, intercept
        
    except ValueError:
        messagebox.showerror("Error", "Ingrese valores numéricos válidos.")
        return None, None
#%%Medir el fondo (I0)
def medir_fondo(barra_progreso_3,ventana):
    #messagebox.showinfo("Medir fondo", "Coloque la cubeta con agua y presione OK para medir el fondo")
    global I0_bis
    I0_bis = medir_intensidad("medir", barra_progreso_3, ventana)
    
    if I0_bis is None:
        messagebox.showerror("Error", "Error en la medición del fondo.")
        barra_progreso_3['value']=0
        return None, None
    
    messagebox.showinfo("Información", f"I0_bis = {I0_bis:.2f}")
    barra_progreso_3['value']=0
    ventana.update_idletasks()
    return I0_bis
    # if (I0 is not None) and (slope is not None) and (intercept is not None):
    #     boton_medir.config(state="normal")  # Habilitar el botón Medir muestra después de calibrar
           
#%% Medir Muestra
def medir_muestra(slope, intercept, I0,barra_progreso_2,ventana):
    """Mide una muestra desconocida y calcula su concentración.
    Se requieren 3 medidas
    """
    if I0 is None or slope is None or intercept is None:
        messagebox.showerror("Error", "No se ha realizado la calibración. Verifique los valores de I0, slope e intercept.")
        return None
    
    MM0=messagebox.askokcancel("Medir fondo", "Coloque la cubeta con agua y presione OK para medir el fondo")
    if not MM0:
        return None
    barra_progreso_2['value'] = 0
    ventana.update_idletasks() 

    I0_bis=medir_fondo(barra_progreso_3,ventana)
    print('I0 bis=',I0_bis)

    dif_relativa_I0=abs((I0_bis-I0)/I0)
    if dif_relativa_I0<0.1:
        print(f'Diferencia relativa en el fondo menor al 10% ({100*dif_relativa_I0})')
    else:
        print(f'Diferencia relativa en el fondo {100*dif_relativa_I0}')
        Cal_again=messagebox.askyesnocancel(title=None, message='Diferencia relativa en el fondo mayor al 10%\nDesea repetir la calibración?')
    if not Cal_again:
        print('aaa')





    MM=messagebox.askokcancel("Medir muestra", "Coloque la muestra en la cubeta y presione OK...")
    if not MM:
        return None
    fecha_nombre_archivo=datetime.now().strftime('%y%m%d_%H%M%S')
    concentraciones = []
    barra_progreso_2['value'] = 0
    ventana.update_idletasks()
    for rep in range(3):
        messagebox.showinfo("Medición", f"Presione OK para iniciar la medición {rep + 1}/3...")
        barra_progreso_3['value'] = 0

        intensidad = medir_intensidad("medir", barra_progreso_3, ventana)
        if intensidad is not None:
            print('I0=',I0)
            print('I=',intensidad)
            absorbancia_muestra = -np.log10(intensidad / I0) #Calculo absorbancia
            print('Absorbancia=',absorbancia_muestra)
            concentracion_muestra = (absorbancia_muestra - intercept) / slope #Calculo concentracion
            concentraciones.append(concentracion_muestra)
            print(f"Concentración {rep+1}: {concentracion_muestra:.2f} mg/ml")
            
            Med=messagebox.askokcancel("Muesta", f"Medición {rep+1}/3\n Concentracion {rep+1} = {concentracion_muestra:.2f} g/L")
            barra_progreso_2['value'] += (1/3)*100  # Avanzar en 1/3
            ventana.update_idletasks()  # Actualizar la interfaz gráfica
            if not Med:
                return None
        #print(f"Absorbancia de la muestra: {absorbancia_muestra:.2f}")
            
    if len(concentraciones) == 3:
        conc_promedio = np.mean(np.array(concentraciones))
        err_conc= np.std(np.array(concentraciones))
        Concentracion=ufloat(conc_promedio,err_conc)
        print(f"Concentracion promedio de la muestra: {Concentracion:.3f} mg/mL")
        
        messagebox.showinfo("Concentracion ", f"Concentración = {Concentracion:.3f}")        
        # nombre_archivo = 
        # with open(nombre_archivo, "w") as archivo:
        #     archivo.write("Intensidad promedio, Absorbancia, Concentración estimada (mg/ml)\n")
        #     archivo.write("Intensidad promedio, Absorbancia, Concentración estimada (mg/ml)\n")
        #     archivo.write(f"{promedio_I:.3f}, {absorbancia_muestra:.3f}, {concentracion_muestra:.3f}\n")
        
        print(f"Datos de la muestra guardados en {nombre_archivo}")
    else:
        print("Error: No se obtuvieron suficientes mediciones.")

#%%  Conexión con Arduino y Configuración del puerto seri
puertos_disponibles = serial.tools.list_ports.comports()  # Listar los puertos seriales disponibles
puerto_activo = None
# Buscar el primer puerto USB activo (ttyUSB*)
for puerto in puertos_disponibles:
    print(f"Puerto: {puerto.device}")
    if "ttyUSB" in puerto.device:  # Verificar si el puerto es ttyUSB*
        try:
            # Intenta abrir el puerto
            conexion = serial.Serial(puerto.device)
            conexion.close()  # Cierra la conexión
            print(f"Puerto activo: {puerto.device}")
            puerto_activo = puerto.device  # Guardar el nombre del puerto activo
            break  # Salir del bucle después de encontrar el primer ttyUSB* activo
        except (serial.SerialException, OSError):
            print(f"Puerto inactivo: {puerto.device}")
    elif "COM" in puerto.device:  # Verificar si el puerto es COM* (windows)
        try:
            # Intenta abrir el puerto
            conexion = serial.Serial(puerto.device)
            conexion.close()  # Cierra la conexión
            print(f"Puerto activo: {puerto.device}")
            puerto_activo = puerto.device  # Guardar el nombre del puerto activo
            break  # Salir del bucle después de encontrar el primer ttyUSB* activo
        except (serial.SerialException, OSError):
            print(f"Puerto inactivo: {puerto.device}")
# Verificar si se encontró un puerto USB activo
if puerto_activo:
    print('-' * 50, '\n', f"Puerto seleccionado: {puerto_activo}")
else:
    print("No se encontraron puertos USB activos.")
    exit()
puerto = puerto_activo  # lo detecta automaticamente para que sea cross plataform 
baudrate = 9600    
################################################################################################################
#%% Ejecución
try:
    ser = serial.Serial(puerto, baudrate, timeout=1)
    time.sleep(2)
    print("Conectado a Arduino.")
    
    slope, intercept, I0 = None, None, None
    ###########################################################################
    # Crear la ventana principal
    ventana = tk.Tk()
    ventana.title("Medición de Absorbancias")
    ventana.geometry("350x320")  # Aumenté el tamaño para acomodar la nueva etiqueta

    frame_botones = tk.Frame(ventana)# Crear un Frame para  "Calibrar" y "Usar Calibración"
    frame_botones.pack(pady=5)

    # Iniciar la calibración (izquierda)
    boton_calibrar = tk.Button(frame_botones, text="Calibrar",  bd=10,bg='orange',command=lambda: calibrar(barra_progreso, ventana))
    boton_calibrar.pack(side=tk.LEFT, padx=5)  # Colocar a la izquierda con un margen

    # Usar una calibración existente (derecha)
    boton_usar_calibracion = tk.Button(frame_botones, text="Usar Calibración",bg='orange', bd=10,command=usar_calibracion)
    boton_usar_calibracion.pack(side=tk.RIGHT, padx=5)
    # Crear una barra de progreso
    barra_progreso = ttk.Progressbar(ventana, orient="horizontal", length=300, mode="determinate")
    barra_progreso.pack(pady=5)
    
    
    ###########################################################################
    frame_2 = tk.Frame(ventana)
    frame_2.pack(pady=5)
    #Medir fondo (izquierda)
    #boton_medir_I0 = tk.Button(frame_2, text="medir fondo",  bd=10,bg='blue',state='disabled',command=lambda: medir_fondo(barra_progreso_3, ventana))
    #boton_medir_I0.pack(side=tk.LEFT, padx=5)  # Colocar a la izquierda con un margen
    # Medir muestra (derecha)
    boton_medir = tk.Button(frame_2, text="Medir muestra",  bd=10,bg='green',state='disabled',
                            command=lambda: medir_muestra(slope, intercept, I0, barra_progreso_2, ventana))
    boton_medir.pack(pady=5)
    # Crear una barra de progreso
    barra_progreso_2 = ttk.Progressbar(ventana, orient="horizontal", length=300, mode="determinate")
    barra_progreso_2.pack(pady=10)
    
    
    ########################################################################
    
    # Etiqueta para la barra de progreso 3
    etiqueta_progreso = tk.Label(ventana, text="Progreso")
    etiqueta_progreso.pack(pady=(10, 0))  # Añade un pequeño margen superior
    # Crear la barra de progreso 3
    barra_progreso_3 = ttk.Progressbar(ventana, orient="horizontal", length=300, mode="determinate")
    barra_progreso_3.pack(pady=(0, 20))  # Añade un pequeño margen inferior
    
    # Botón para salir 
    boton_salir = tk.Button(ventana, bd=10,bg='red', text="Salir", command=ventana.destroy)
    boton_salir.pack(pady=10)
    
    # Iniciar el bucle principal de la ventana
    ventana.mainloop()
    
except serial.SerialException:
    messagebox.showerror("Error", f"No se pudo abrir el puerto {puerto}. Verifique la conexión.")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
    print("Conexión cerrada.")