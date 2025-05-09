#%% Librerías
import serial
import serial.tools.list_ports
import time
import numpy as np
import scipy.stats as stats
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, filedialog, scrolledtext
from uncertainties import ufloat, unumpy
import matplotlib.pyplot as plt
import os
import chardet
#%% 23 Abr 25 cuadro de props de muestra
class ParamsMuestra(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Parámetros de la muestra")
        self.geometry("400x180")  
        
        # Generar nombre por defecto
        default_name = "muestra_" + datetime.now().strftime("%y%m%d_%H%M%S")
        
        # Marco principal para mejor organización
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(expand=True, fill='both')
        
        # Campo 1: Nombre de muestra
        tk.Label(main_frame, text="Nombre de muestra:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_entry = tk.Entry(main_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.name_entry.insert(0, default_name)
        
        # Campo 2: Factor de dilución
        tk.Label(main_frame, text="Factor de dilución (≥1):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.dilution_entry = tk.Entry(main_frame)
        self.dilution_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.dilution_entry.insert(0, "1.0")
        
        # Campo 3: Número de alícuotas
        tk.Label(main_frame, text="Número de alícuotas:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.aliquots_entry = tk.Entry(main_frame)
        self.aliquots_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.aliquots_entry.insert(0, "3")
        
        # Configurar expansión de columnas
        main_frame.columnconfigure(1, weight=1)
        
        # Botón Aceptar
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        tk.Button(button_frame, text="Aceptar",  
                 command=self.on_accept, width=10).pack(side=tk.RIGHT, padx=5)
        
        self.result = None
    
    def on_accept(self):
        try:
            # Validar y obtener los valores
            nombre = self.name_entry.get().strip()
            if not nombre:
                raise ValueError("El nombre de la muestra no puede estar vacío")
                
            factor = float(self.dilution_entry.get())
            if factor <= 0:
                raise ValueError("El factor de dilución debe ser mayor que 0")
                
            alicuotas = int(self.aliquots_entry.get())
            if alicuotas <= 0:
                raise ValueError("El número de alícuotas debe ser mayor que 0")
            
            self.result = (nombre, factor, alicuotas)
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error de validación", f"Dato inválido:\n{str(e)}")
            if "factor" in str(e).lower():
                self.dilution_entry.focus_set()
            elif "alícuotas" in str(e).lower():
                self.aliquots_entry.focus_set()
            else:
                self.name_entry.focus_set()
#%% Medir Intensidad c/Arduino
def medir_intensidad(comando,num_medidas=1, barra_progreso=None, ventana=None):
    """Mide la intensidad del sensor (I0 o I) según el comando dado y devuelve el promedio de 10 mediciones."""
    mediciones = []  # Lista para almacenar las mediciones individuales

    for i in range(num_medidas):  # Realizar 10 mediciones
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
            barra_progreso['value'] = (i + 1)*num_medidas # Avanzar en 10% por cada medición
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
    global I0,slope, intercept,err_slope,err_intercept  # Declarar slope e intercept como globales
    print('-' * 50, '\nUso calibracion existente')
    
    # Abrir un diálogo para seleccionar un archivo .txt
    archivo_calibracion = filedialog.askopenfilename(filetypes=[('Archivos de texto/datos', '*.txt *.dat')])
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
                        err_slope=float(slope_str.split("+/-")[1].strip())
                    elif "Ordenada:" in linea:
                        intercept_str = linea.split(":")[1].strip()  # Extraer el valor de la ordenada
                        intercept = float(intercept_str.split("+/-")[0].strip())  # Obtener el valor numérico
                        err_intercept=float(intercept_str.split("+/-")[1].strip())
                    elif "Fondo:" in linea:
                        fondo_str = linea.split(":")[1].strip()  # Extraer el valor del fondo
                        I0 = float(fondo_str)  # Obtener el valor numérico
                
                # Verificar si todos los valores necesarios se cargaron correctamente
                if (I0 is not None) and (slope is not None) and (intercept is not None):
                    barra_progreso['value'] = 100
                    print(f"Valores cargados:\nFondo: {I0} cuentas\nPendiente: {ufloat(slope,err_slope)}\nOrdenada: {ufloat(intercept,err_intercept)}")
                    messagebox.showinfo("Uso calibración previa", f"Valores cargados:\nFondo: {I0} cnts\nPendiente: {ufloat(slope,err_slope)}\nOrdenada: {ufloat(intercept,err_intercept)}")
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
    global slope, intercept,I0_cal,err_slope,err_intercept  # Declarar I0_cal, slope e intercept como globales    
    try:
        conc_madre = simpledialog.askfloat("Concentración madre", "Ingrese la concentración madre (mg/ml):")# Solicitar la concentración madre
        if conc_madre is None:  # Si el usuario cancela
            return None, None
        
        diluciones = [500, 250, 200, 125, 100, 80]
        concentraciones = [conc_madre / d for d in diluciones]
        
        # Medir el fondo (I0)
        messagebox.showinfo("Medir fondo", "Coloque la cubeta con agua y presione OK para medir el fondo")
        
        I0_cal = medir_intensidad("medir", 10,barra_progreso_3, ventana)
        if I0_cal is None:
            messagebox.showerror("Error", "Error en la medición del fondo.")
            barra_progreso_3['value']=0
            return None, None
        print(f'I0 cal = {I0_cal}')     
        messagebox.showinfo("Información", f"I0 = {I0_cal:.2f}")
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
                I = medir_intensidad("medir", 1,barra_progreso_3, ventana)
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
                print(f'A = {-np.log10(promedio_I/I0_cal)}')
                #err_I = np.std(mediciones)
                #errores_I.append(err_I)
                #messagebox.showinfo("Promedio", f"Promedio para la dilución 1/{diluciones[i]}: {ufloat(promedio_I,err_I):.2f}")
        
        absorbancias = [-np.log10(I / I0_cal) for I in valores_I]
        
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
            archivo.write(f"\nFondo: {I0_cal:.3f}\nPendiente: {pendiente:.3f}\nOrdenada: {ordenada:.3f}\nR² = {resultado.rvalue**2:.2f}\n")
        
        messagebox.showinfo("Guardado", f"Datos guardados en {output_dir}")
        if (I0_cal is not None) and (slope is not None) or (intercept is not None):
            boton_medir.config(state="active")  # Habilitar el botón Medir muestra después de calibrar
            #boton_medir_I0.config(state="disabled")
        
        return I0_cal,slope, intercept
        
    except ValueError:
        messagebox.showerror("Error", "Ingrese valores numéricos válidos.")
        return None, None
#%%Medir el fondo (I0)
def medir_fondo(barra_progreso_3,ventana):
    #messagebox.showinfo("Medir fondo", "Coloque la cubeta con agua y presione OK para medir el fondo")
    global I0
    I0 = medir_intensidad("medir", 10,barra_progreso_3, ventana)
    
    if I0 is None:
        messagebox.showerror("Error", "Error en la medición del fondo.")
        barra_progreso_3['value']=0
        return None, None
    
    messagebox.showinfo("Información", f"I0 = {I0:.2f}")
    barra_progreso_3['value']=0
    ventana.update_idletasks()
    return I0
    # if (I0 is not None) and (slope is not None) and (intercept is not None):
    #     boton_medir.config(state="normal")  # Habilitar el botón Medir muestra después de calibrar
           
#%% Medir Muestra
def medir_muestra(slope,err_slope,intercept,err_intercept, I0_cal, barra_progreso_2, ventana):
    """
    Mide una muestra desconocida y calcula su concentración.
    Se requieren 3 medidas
    """
    if slope is None or intercept is None:
        messagebox.showerror("Error", "No se ha realizado/cargado la calibración. Verifique los valores de slope e intercept.")
        return None
    print('-'*50,'\nMedida de muestra iniciada')
    
    nombre_muestra = "muestra_" + datetime.now().strftime("%y%m%d_%H%M%S")
    factor_dilucion = 1.0
    num_alicuotas = 3
    
    MM0 = messagebox.askokcancel("Medir intensidad de fondo I0", "Coloque la cubeta con agua y presione OK continuar")
    if not MM0:
        return None
    barra_progreso_2['value'] = 0
    ventana.update_idletasks() 

    I0 = medir_fondo(barra_progreso_3, ventana)
    print('I0 =', I0, 'cuentas')
    dif_relativa_I0 = abs((I0 - I0_cal)/I0_cal)
    
    if dif_relativa_I0 > 0.1:
        print(f'Diferencia relativa en el fondo {100*dif_relativa_I0:1f}%')
        Cal_again = messagebox.askyesnocancel(title=None, 
                            message='Diferencia relativa en el fondo mayor al 10%\nDesea repetir la calibración?')
        if Cal_again is True:
            print("El usuario eligió calibrar de nuevo")
            calibrar(barra_progreso, ventana)
        elif Cal_again is False:
            print("El usuario eligió continuar con la medida")
            dialog = ParamsMuestra(ventana)
            ventana.wait_window(dialog)
            if not dialog.result:
                return None
            nombre_muestra, factor_dilucion, num_alicuotas = dialog.result
            print(f"Parámetros de la muestra:\n Nombre: {nombre_muestra}\n Factor de dilución: {factor_dilucion}\n Num de alicuotas a medir: {num_alicuotas}")

        else:
            return None
    else:
        print(f'Diferencia relativa en el fondo menor al 10% ({100*dif_relativa_I0})')
        dialog = ParamsMuestra(ventana)
        ventana.wait_window(dialog)
        if not dialog.result:
            return None  
        nombre_muestra, factor_dilucion, num_alicuotas = dialog.result
        print(f"Parámetros de la muestra:\n Nombre: {nombre_muestra}\n Factor de dilución: {factor_dilucion}\n Num de alicuotas a medir: {num_alicuotas}")
     
    fecha_nombre_archivo = datetime.now().strftime('%y%m%d_%H%M%S')
    intensidades, absorbancias, s_absorbancias = [], [], []
    intensidades_todas, absorbancias_todas, concentraciones_todas = [], [], []
    
    barra_progreso_2['value'] = 0
    ventana.update_idletasks()

    for alic in range(num_alicuotas): #Loop de alicuotas
        print(f'\nAlicuota {alic+1}/{num_alicuotas}')
        MM = messagebox.askokcancel(f"Medir muestra - Alicuota {alic+1}/{num_alicuotas}",f"Coloque la muestra en la cubeta y presione OK para iniciar la medición de la alicuota {alic+1}")
        if not MM:
            return None
        
        intensidades_alic, absorbancias_alic, concentraciones_alic = [], [], []
        for rep in range(3): # Loop de las 3 mediciones por alicuota
            barra_progreso_3['value'] = 0
            intensidad = medir_intensidad("medir", 1,barra_progreso_3, ventana)
            if intensidad is not None:
                #print('I0 =', I0, 'cuentas')
                print('I =', intensidad, 'cuentas')
                intensidades_alic.append(intensidad)
                intensidades_todas.append(intensidad)
                absorbancia_muestra = -np.log10(intensidad / I0)
                absorbancias_alic.append(absorbancia_muestra)
                absorbancias_todas.append(absorbancia_muestra)
                print('Absorbancia =', absorbancia_muestra)

                Med = messagebox.askokcancel(f'Medir muestra - alicuota {alic+1}/{num_alicuotas}', 
                    f"Medición {rep+1}/{3}\nAbsorbancia {rep+1} = {absorbancia_muestra:.2e}")
                barra_progreso_2['value'] += (1/3)*100
                ventana.update_idletasks()
                if not Med:
                    return None
        #CALCULO PROMEDIO X ALICUOTA
        absorbancia_prom_alic=np.mean(absorbancias_alic)
        err_absorbancia_alic =np.std(absorbancias_alic,ddof=1)
        err_absorbancia_alic_prom=err_absorbancia_alic/np.sqrt(3)
        
        absorbancias.append(absorbancia_prom_alic)
        s_absorbancias.append(err_absorbancia_alic_prom)
        print('Absorbancia x alicuota', ufloat(absorbancia_prom_alic,err_absorbancia_alic_prom),'\n')
        
    if len(absorbancias_todas) == 3*num_alicuotas:
        print(f'\nPromediado para para las {num_alicuotas} alicuotas:')

        A_final=np.mean(absorbancias)
        S_combinada=np.sqrt(sum(x**2 for x in s_absorbancias)/num_alicuotas)
        S_final = S_combinada/np.sqrt(num_alicuotas)
 
        print('Absorbancia final =',A_final,S_final)
        
        #Calculo Concentracion
        Conc= (A_final-intercept)/slope
        err_Conc= np.sqrt((err_intercept/slope)**2 + (S_final/slope)**2 + ((A_final-intercept)*err_slope/(slope**2))**2)
        Concentracion = ufloat(Conc,err_Conc)*factor_dilucion
        
        print(f"\nConcentracion de la muestra: {Concentracion:.3e} g/L")
        
        # Usar el nombre que ingresó el usuario
        nombre_archivo = f'{nombre_muestra}.txt' if not nombre_muestra.endswith('.txt') else nombre_muestra

        with open(nombre_archivo, "w") as archivo:
            archivo.write(f'#{fecha_nombre_archivo}\n')
            archivo.write('-'*15+' Parametros de muestra '+'-'*15+'\n')
            archivo.write(f" Nombre muestra: {nombre_muestra}\n")
            archivo.write(f" Factor dilución: {factor_dilucion}\n")
            archivo.write(f" Número alícuotas: {num_alicuotas}\n")
            archivo.write('-'*20+' Calibracion '+'-'*20 +'\n')
            archivo.write(f" Fondo calibracion I0_cal= {I0_cal} cuentas \n Pendiente = {slope:.3e} \n Ordenada = {intercept:.3e}\n")
            archivo.write('-'*22 +' Medida '+'-'*22 +'\n')
            archivo.write(f" Fondo I0 = {I0} cuentas\n")
            archivo.write(f"\nIntensidad (I) | Absorbancia (A) \n")
            
            for i, a in zip(intensidades_todas, absorbancias_todas):
                archivo.write(f"{i:10.2f}{a:10.3e}\n")
            archivo.write(f"\nConcentracion de la muestra: {Concentracion:.3e} g/L")
                    
        messagebox.showinfo("Concentración", f"Concentración = {Concentracion:.3e} g/L")        
        print(f"Datos de la muestra guardados en {nombre_archivo}")
    else:
        print("Error: No se obtuvieron suficientes mediciones.")

#%% Conexión con Arduino y Configuración del puerto seri
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
    ventana.title("G3M - Concentrímetro")
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
                            command=lambda: medir_muestra(slope,err_slope,intercept,err_intercept,I0, barra_progreso_2, ventana))
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