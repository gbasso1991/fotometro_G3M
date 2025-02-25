#%% Librerías
import serial
import serial.tools.list_ports
import time
import numpy as np
import scipy.stats as stats
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
from uncertainties import ufloat, unumpy
import matplotlib.pyplot as plt
#%% Funciones
def obtener_nombre_archivo(prefijo):
    """Genera un nombre de archivo único basado en la fecha y hora actual."""
    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefijo}_{fecha_hora}.txt"

def medir_intensidad(comando):
    """Mide la intensidad del sensor (I0 o I) según el comando dado y devuelve el valor obtenido."""
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
                return I  # Retorna la intensidad medida
            except ValueError:
                print(f"Error al convertir datos: {linea}")
                return None
    except Exception as e:
        print(f"Error en la medición: {e}")
        return None
#%% Calibrar
def calibrar(barra_progreso, ventana):
    """Realiza la calibración midiendo intensidades de soluciones conocidas.
    Se ingresa la concentracion de la solucion madre y luego se miden las concentraciones de las diluciones: [1/500, 1/250, 1/200, 1/125, 1/100, 1/80] (3 veces c/u)
    A partir de estos datos se calibra la recta Concentracion/Absorbancia
    Se mide la muestra incognita (3 veces) y de acuerdo a la calibracion se determina la concentracion"""
    try:
        # Solicitar la concentración madre
        conc_madre = simpledialog.askfloat("Concentración madre", "Ingrese la concentración madre (mg/ml):")
        if conc_madre is None:  # Si el usuario cancela
            return None, None
        
        diluciones = [500, 250, 200, 125, 100, 80]
        concentraciones = [conc_madre / d for d in diluciones]
        
        # Medir el fondo (I0)
        messagebox.showinfo("Medir fondo", "Coloque la cubeta con agua y presione OK para medir el fondo...")
        I0 = medir_intensidad("medir")
        if I0 is None:
            messagebox.showerror("Error", "Error en la medición de I_0.")
            return None, None
        
        messagebox.showinfo("Información", f"I0 = {I0:.2f}")
        
        barra_progreso['value'] = 0
        ventana.update_idletasks()
        valores_I,errores_I = [],[]
        for i, dil in enumerate(diluciones):
            MS=messagebox.askokcancel(f"Medir dilución 1/{dil}", f"Coloque la solución de dilución 1/{diluciones[i]} y presione OK...")
            if not MS:
                barra_progreso['value'] = 0
                ventana.update_idletasks()
                return None
            
            mediciones = []
            
            for _ in range(3):
                I = medir_intensidad("medir")
                if I is not None:
                    mediciones.append(I)
                    messagebox.showinfo(f"Dilución 1/{dil}", f"Medición {_+1}/3: I = {I:.2f}")
                    # Actualizar la barra de progreso
                    barra_progreso['value'] += (1 / 18) * 100  # Avanzar en 1/18 (3 medidas x 6 diluciones)
                    ventana.update_idletasks()  # Actualizar la interfaz gráfica
            
            if len(mediciones) == 3:
                promedio_I = np.mean(mediciones)
                err_I = np.std(mediciones)
                valores_I.append(promedio_I)
                errores_I.append(err_I)
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
            archivo.write("Concentracion (mg/ml), Absorbancia\n")
            for c, A in zip(concentraciones, absorbancias):
                archivo.write(f"{c:.2f}, {A:.2f}\n")
            archivo.write(f"\nPendiente: {pendiente:.3f}\nOrdenada: {ordenada:.3f}\nR² = {resultado.rvalue**2:.2f}\n")
        
        messagebox.showinfo("Guardado", f"Datos guardados en {output_dir}")
        
        return slope, intercept
        
    except ValueError:
        messagebox.showerror("Error", "Ingrese valores numéricos válidos.")
        return None, None
#%% Medir
def medir_muestra(slope, intercept, I0,barra_progreso_2,ventana):
    """Mide una muestra desconocida y calcula su concentración.
    Se requieren 3 medidas
    """
    MM=messagebox.askokcancel("Medir muestra", "Coloque la muestra en la cubeta y presione OK...")
    if not MM:
        return None
    mediciones = []
    barra_progreso_2['value'] = 0
    ventana.update_idletasks()
    for rep in range(3):
        messagebox.showinfo("Medición", f"Presione OK para iniciar la medición {rep + 1}/3...")
        intensidad = medir_intensidad("medir")
        if intensidad is not None:
            mediciones.append(intensidad)
            Med=messagebox.askokcancel("Medición", f"Medición {rep+1}/3: I = {intensidad:.2f}")
            barra_progreso_2['value'] += (1/3)*100  # Avanzar en 1/3
            ventana.update_idletasks()  # Actualizar la interfaz gráfica
            if not Med:
                return None
    if len(mediciones) == 3:
        promedio_I = np.mean(mediciones)
        print(f"Intensidad promedio de la muestra: {promedio_I:.2f}")
        
        absorbancia_muestra = -np.log10(promedio_I / I0)
        print(f"Absorbancia de la muestra: {absorbancia_muestra:.2f}")
        
        concentracion_muestra = (absorbancia_muestra - intercept) / slope
        print(f"Concentración estimada: {concentracion_muestra:.2f} mg/ml")
        
        nombre_archivo = obtener_nombre_archivo("muestra")
        with open(nombre_archivo, "w") as archivo:
            archivo.write("Intensidad promedio, Absorbancia, Concentración estimada (mg/ml)\n")
            archivo.write(f"{promedio_I:.2f}, {absorbancia_muestra:.2f}, {concentracion_muestra:.2f}\n")
        
        print(f"Datos de la muestra guardados en {nombre_archivo}")
    else:
        print("Error: No se obtuvieron suficientes mediciones.")

#%% Ejecución
# Listar los puertos seriales disponibles
puertos_disponibles = serial.tools.list_ports.comports()

# Verificar cuáles están activos
for puerto in puertos_disponibles:
    try:
        # Intenta abrir el puerto
        conexion = serial.Serial(puerto.device)
        conexion.close()  # Cierra la conexión
        print(f"Puerto activo: {puerto.device}")
    except (serial.SerialException, OSError):
        pass
        # Si no se puede abrir, el puerto no está activo
        #print(f"Puerto inactivo: {puerto.device}")
# Configura el puerto serie
puerto = '/dev/ttyUSB0'  # Cambia esto según tu sistema
baudrate = 9600

try:
    ser = serial.Serial(puerto, baudrate, timeout=1)
    time.sleep(2)
    print("Conectado a Arduino.")
    
    slope, intercept, I0 = None, None, None
    
    # Crear la ventana principal
    ventana = tk.Tk()
    ventana.title("Medición de Absorbancias")
    ventana.geometry("350x280") 

    # Botón para iniciar la calibración
    boton_calibrar = tk.Button(ventana, text="Calibrar", command=lambda: calibrar(barra_progreso, ventana))
    boton_calibrar.pack(pady=10)

    # Crear una barra de progreso
    barra_progreso = ttk.Progressbar(ventana, orient="horizontal", length=300, mode="determinate")
    barra_progreso.pack(pady=20)
    
    # Botón para medir muestra
    boton_medir = tk.Button(ventana, text="Medir muestra", command=lambda: medir_muestra(slope, intercept, I0,barra_progreso_2,ventana))
    boton_medir.pack(pady=10)
    
    # Crear una barra de progreso
    barra_progreso_2 = ttk.Progressbar(ventana, orient="horizontal", length=300, mode="determinate")
    barra_progreso_2.pack(pady=20)
    
    # Botón para salir 
    boton_salir = tk.Button(ventana, text="Salir", command=ventana.destroy)
    boton_salir.pack(pady=10)
    
    # Iniciar el bucle principal de la ventana
    ventana.mainloop()
    
except serial.SerialException:
    messagebox.showerror("Error", f"No se pudo abrir el puerto {puerto}. Verifique la conexión.")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
    print("Conexión cerrada.")


# %%
