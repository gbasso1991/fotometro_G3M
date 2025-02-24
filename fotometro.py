#%% Librerias
import serial
import time
import os
import numpy as np
import scipy.stats as stats
import keyboard
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox

#%% Funciones Seba
def obtener_nombre_archivo(prefijo):
    fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{prefijo}_{fecha_hora}.txt"

def medir_intensidad(comando):
    """Mide la intensidad del sensor (I0 o I) según el comando dado y devuelve el valor obtenido.
    Los comandos pueden ser: 'medir' / 'calibrar' """
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

def calibrar():
    """Realiza la calibración midiendo intensidades de soluciones conocidas.
    Son 6 diluciones, con 3 medidas c/u"""
    try:
        conc_madre = input("Ingrese la concentración madre (mg/ml): ").strip().replace(",", ".")
        conc_madre = float(conc_madre)
        
        diluciones = [500, 250, 200, 125, 100, 80]
        concentraciones = [conc_madre / d for d in diluciones]
        
        input("Coloque la cubeta con agua y presione Enter para medir el fondo...")
        I0 = medir_intensidad("medir")
        
        if I0 is None:
            print("Error en la medición de I0.")
            return None, None
        
        print(f"I0 = {I0:.2f}")
        
        valores_I = []
        for i, dil in enumerate(diluciones):
            input(f"Coloque la solución de dilución 1/{diluciones[i]} y presione Enter...")
            mediciones = []
            for _ in range(3):
                
                I = medir_intensidad("medir")
                if I is not None:
                    mediciones.append(I)
                    print(f"Medición {_+1}/3: I = {I:.2f}")
                    input(f"Presione Enter para continuar")
            if len(mediciones) == 3:
                promedio_I = np.mean(mediciones)
                valores_I.append(promedio_I)
                print(f"Promedio para la dilución 1/{diluciones[i]}: {promedio_I:.2f}")
        
        absorbancias = [-np.log10(I / I0) for I in valores_I]
        
        print("Absorbancias calculadas:", *[f"{a:.5g}" for a in absorbancias])

        
        slope, intercept, r_value, _, _ = stats.linregress(concentraciones, absorbancias)
        print(f"Ajuste de calibración: y = {slope:.2f}x + {intercept:.2f}, R² = {r_value**2:.2f}")
        
        nombre_archivo = obtener_nombre_archivo("calibracion")
        with open(nombre_archivo, "w") as archivo:
            archivo.write("Concentracion (mg/ml), Absorbancia\n")
            for c, A in zip(concentraciones, absorbancias):
                archivo.write(f"{c:.2f}, {A:.2f}\n")
            archivo.write(f"\nEcuación: y = {slope:.2f}x + {intercept:.2f}, R² = {r_value**2:.2f}\n")
        
        print(f"Calibración completada. Datos guardados en {nombre_archivo}")
        
        return slope, intercept  
        # aca tendria que sacar un grafico con la recta de calibracion
    
    except ValueError:
        print("Error: Ingrese valores numéricos válidos.")
        return None, None

def medir_muestra(slope, intercept, I0):
    """Mide una muestra desconocida y calcula su concentración a partir de la recta de calibración."""
    input("Coloque la muestra en la cubeta y presione Enter...")
    
    mediciones = []
    for rep in range(3):
        input(f"Presione Enter para iniciar la medición {rep + 1}/3...")
        intensidad = medir_intensidad("medir")
        if intensidad is not None:
            mediciones.append(intensidad)
            print(f"Medición {rep+1}/3: I = {intensidad:.2f}")
    
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
        
        # aca el grafico de la muestra incognita respecto a la calibracion
    else:
        print("Error: No se obtuvieron suficientes mediciones.")

#%% Ejecucion Seba
try:
    ser = serial.Serial(puerto, baudrate, timeout=1)
    time.sleep(2)
    print("Conectado a Arduino.")
    
    slope, intercept, I0 = None, None, None  
    while True:
        print("\nOpciones:")
        print("1 - Calibrar")
        print("2 - Medir muestra")
        print("3 - Salir")
        
        opcion = input("Ingrese una opción: ").strip()
        
        if opcion == "1":
            slope, intercept = calibrar()
        elif opcion == "2":
            if slope is None or intercept is None:
                print("Debe realizar la calibración antes de medir muestras.")
            else:
                medir_muestra(slope, intercept, I0)
        elif opcion == "3":
            print("Saliendo del programa.")
            break
        else:
            print("Opción no válida.")
except serial.SerialException:
    print(f"Error: No se pudo abrir el puerto {puerto}. Verifique la conexión.")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
    print("Conexión cerrada.")





#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
import serial
import time
import numpy as np
import scipy.stats as stats
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox

# Configura el puerto serie
puerto = '/dev/ttyUSB0'  # Cambia esto según tu sistema
baudrate = 9600

# Variable global para I0
I0 = None

def obtener_nombre_archivo(prefijo):
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
                #messagebox.showinfo("Procesando", "Procesando...")
                continue  # Sigue esperando el dato real
            try:
                I = float(linea)
                return I  # Retorna la intensidad medida
            except ValueError:
                messagebox.showerror("Error", f"Error al convertir datos: {linea}")
                return None
    except Exception as e:
        messagebox.showerror("Error", f"Error en la medición: {e}")
        return None

def calibrar():
    """Realiza la calibración midiendo intensidades de soluciones conocidas."""
    try:
        global I0  # Usar la variable global I0
        conc_madre = simpledialog.askfloat("Concentración madre", "Ingrese la concentración madre (mg/ml):")
        if conc_madre is None:  # Si el usuario cancela
            return None, None
        
        diluciones = [500, 250, 200, 125, 100, 80]
        concentraciones = [conc_madre / d for d in diluciones]
        
        # Medir el fondo (I0)
        messagebox.showinfo("Medir fondo", "Coloque la cubeta con agua y presione OK para medir el fondo...")
        I0 = medir_intensidad("medir")
        
        if I0 is None:
            messagebox.showerror("Error", "Error en la medición de I0.")
            return None, None
        
        valores_I = []
        for i, dil in enumerate(diluciones):
            while True:  # Bucle para permitir repetir las mediciones
                messagebox.showinfo("Medir solución", f"Coloque la solución de dilución 1/{diluciones[i]} y presione OK...")
                mediciones = []
                for _ in range(3):
                    I = medir_intensidad("medir")
                    if I is not None:
                        mediciones.append(I)
                        messagebox.showinfo("Medición", f"Medición {_+1}/3: I = {I:.2f}")
                
                if len(mediciones) == 3:
                    promedio_I = np.mean(mediciones)
                    valores_I.append(promedio_I)
                    
                    # Preguntar si desea repetir las mediciones
                    respuesta = messagebox.askyesno("Promedio", 
                                                  f"Promedio para la dilución 1/{diluciones[i]}: {promedio_I:.2f}\n¿Desea repetir las mediciones?")
                    if not respuesta:  # Si el usuario elige "No"
                        break  # Salir del bucle y continuar con la siguiente dilución
                    else:
                        valores_I.pop()  # Elimina el promedio anterior para repetir
        
        absorbancias = [-np.log10(I / I0) for I in valores_I]
        
        slope, intercept, r_value, _, _ = stats.linregress(concentraciones, absorbancias)
        messagebox.showinfo("Calibración completada", f"Ajuste de calibración: y = {slope:.2f}x + {intercept:.2f}, R² = {r_value**2:.2f}")
        
        nombre_archivo = obtener_nombre_archivo("calibracion")
        with open(nombre_archivo, "w") as archivo:
            archivo.write("Concentracion (mg/ml), Absorbancia\n")
            for c, A in zip(concentraciones, absorbancias):
                archivo.write(f"{c:.2f}, {A:.2f}\n")
            archivo.write(f"\nEcuación: y = {slope:.2f}x + {intercept:.2f}, R² = {r_value**2:.2f}\n")
        
        messagebox.showinfo("Guardado", f"Datos guardados en {nombre_archivo}")
        
        return slope, intercept
        
    except ValueError:
        messagebox.showerror("Error", "Ingrese valores numéricos válidos.")
        return None, None

def medir_muestra(slope, intercept, I0):
    """Mide una muestra desconocida y calcula su concentración."""
    messagebox.showinfo("Medir muestra", "Coloque la muestra en la cubeta y presione OK...")
    
    mediciones = []
    for rep in range(3):
        messagebox.showinfo("Medición", f"Presione OK para iniciar la medición {rep + 1}/3...")
        intensidad = medir_intensidad("medir")
        if intensidad is not None:
            mediciones.append(intensidad)
            messagebox.showinfo("Medición", f"Medición {rep+1}/3: I = {intensidad:.2f}")
    
    if len(mediciones) == 3:
        promedio_I = np.mean(mediciones)
        absorbancia_muestra = -np.log10(promedio_I / I0)
        concentracion_muestra = (absorbancia_muestra - intercept) / slope
        
        nombre_archivo = obtener_nombre_archivo("muestra")
        with open(nombre_archivo, "w") as archivo:
            archivo.write("Intensidad promedio, Absorbancia, Concentración estimada (mg/ml)\n")
            archivo.write(f"{promedio_I:.2f}, {absorbancia_muestra:.2f}, {concentracion_muestra:.2f}\n")
        
        messagebox.showinfo("Resultado", f"Concentración estimada: {concentracion_muestra:.2f} mg/ml\nDatos guardados en {nombre_archivo}")
    else:
        messagebox.showerror("Error", "No se obtuvieron suficientes mediciones.")

def calibrar_interfaz():
    slope, intercept = calibrar()
    if slope is not None and intercept is not None:
        messagebox.showinfo("Calibración completada", f"Ecuación: y = {slope:.2f}x + {intercept:.2f}")

def medir_muestra_interfaz():
    if slope is None or intercept is None:
        messagebox.showerror("Error", "Debe realizar la calibración antes de medir muestras.")
    else:
        medir_muestra(slope, intercept, I0)

def salir():
    if 'ser' in globals() and ser.is_open:  # Verificar si 'ser' está definido y abierto
        ser.close()
    ventana.destroy()
    print("Conexión cerrada.")

#%% Ejecución
try:
    ser = serial.Serial(puerto, baudrate, timeout=1)
    time.sleep(2)
    print("Conectado a Arduino.")
    
    slope, intercept = None, None
    
    # Crear la ventana principal
    ventana = tk.Tk()
    ventana.title("Medición de Absorbancias")
    
    # Botón para calibrar
    boton_calibrar = tk.Button(ventana, text="Calibrar", command=calibrar_interfaz)
    boton_calibrar.pack(pady=10)
    
    # Botón para medir muestra
    boton_medir = tk.Button(ventana, text="Medir muestra", command=medir_muestra_interfaz)
    boton_medir.pack(pady=10)
    
    # Botón para salir
    boton_salir = tk.Button(ventana, text="Salir", command=salir)
    boton_salir.pack(pady=10)
    
    # Iniciar el bucle principal de la ventana
    ventana.mainloop()
    
except serial.SerialException:
    messagebox.showerror("Error", f"No se pudo abrir el puerto {puerto}. Verifique la conexión.")
except Exception as e:
    messagebox.showerror("Error", f"Error inesperado: {e}")
finally:
    if 'ser' in globals() and ser.is_open:
        ser.close()
    print("Conexión cerrada.")






# %%
# Crear la ventana principal
ventana = tk.Tk()
ventana.title("Medición de Absorbancias")

# Botón para calibrar
boton_calibrar = tk.Button(ventana, text="Calibrar", command=calibrar_interfaz)
boton_calibrar.pack(pady=10)

# Botón para medir muestra
boton_medir = tk.Button(ventana, text="Medir muestra", command=medir_muestra_interfaz)
boton_medir.pack(pady=10)

# Botón para salir
boton_salir = tk.Button(ventana, text="Salir", command=salir)
boton_salir.pack(pady=10)

# Iniciar el bucle principal de la ventana
ventana.mainloop()
#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#%% Librerías
import serial
import time
import numpy as np
import scipy.stats as stats
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox
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
#%%
def medir_y_promediar(dilucion):
    """Realiza 3 mediciones para una dilución y devuelve el promedio."""
    mediciones = []
    for _ in range(3):
        I = medir_intensidad("medir")
        if I is not None:
            mediciones.append(I)
            print(f"Medición {_+1}/3: I = {I:.2f}")
            input("Presione Enter para continuar")
    if len(mediciones) == 3:
        return np.mean(mediciones),np.std(mediciones)
    return None,None

def calibrar():
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
        
        valores_I,errores_I = [],[]
        for i, dil in enumerate(diluciones):
            MS=messagebox.askokcancel("Medir solución", f"Coloque la solución de dilución 1/{diluciones[i]} y presione OK...")
            if not MS:
                return None
                #messagebox.askyesno(title=None, message='Desea cancelar la calibracion?')
            mediciones = []
            for _ in range(3):
                I = medir_intensidad("medir")
                if I is not None:
                    mediciones.append(I)
                    messagebox.showinfo("Medición", f"Medición {_+1}/3: I = {I:.2f}")
            
            if len(mediciones) == 3:
                promedio_I = np.mean(mediciones)
                err_I = np.std(mediciones)
                valores_I.append(promedio_I)
                errores_I.append(err_I)
                messagebox.showinfo("Promedio", f"Promedio para la dilución 1/{diluciones[i]}: {ufloat(promedio_I,err_I):.2f}")
        
        absorbancias = [-np.log10(I / I0) for I in valores_I]
        
        slope, intercept, r_value, _, _ = stats.linregress(concentraciones, absorbancias)
        messagebox.showinfo("Calibración completada", f"Ajuste de calibración: y = {slope:.2f}x + {intercept:.2f}, R² = {r_value**2:.2f}")
        
        x=np.linspace(diluciones[0],diluciones[-1],1000)
        y=x*slope+intercept
        fig, ax=plt.subplots(constrained_layout=True)
        ax.plot(x,y)
        ax.scatter(diluciones,absorbancias)
        ax.grid()
        ax.set_xlabel('Concentracion')
        ax.set_ylabel('Absorbancia')        
        
        plt.show()
        
        nombre_archivo = obtener_nombre_archivo("calibracion")
        with open(nombre_archivo, "w") as archivo:
            archivo.write("Concentracion (mg/ml), Absorbancia\n")
            for c, A in zip(concentraciones, absorbancias):
                archivo.write(f"{c:.2f}, {A:.2f}\n")
            archivo.write(f"\nEcuación: y = {slope:.2f}x + {intercept:.2f}, R² = {r_value**2:.2f}\n")
        
        messagebox.showinfo("Guardado", f"Datos guardados en {nombre_archivo}")
        
        return slope, intercept
        
    except ValueError:
        messagebox.showerror("Error", "Ingrese valores numéricos válidos.")
        return None, None
#%%
def medir_muestra(slope, intercept, I0):
    """Mide una muestra desconocida y calcula su concentración.
    Se requieren 3 medidas
    """
    MM=messagebox.askokcancel("Medir muestra", "Coloque la muestra en la cubeta y presione OK...")
    if not MM:
        return None
    mediciones = []
    for rep in range(3):
        messagebox.showinfo("Medición", f"Presione OK para iniciar la medición {rep + 1}/3...")
        intensidad = medir_intensidad("medir")
        if intensidad is not None:
            mediciones.append(intensidad)
            Med=messagebox.askokcancel("Medición", f"Medición {rep+1}/3: I = {intensidad:.2f}")
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
    ventana.geometry("350x150") 

    # Botón para calibrar
    boton_calibrar = tk.Button(ventana, text="Calibrar", command=calibrar)
    boton_calibrar.pack(pady=10)
    
    # Botón para medir muestra
    boton_medir = tk.Button(ventana, text="Medir muestra", command=lambda: medir_muestra(slope, intercept, I0))
    boton_medir.pack(pady=10)
    
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
