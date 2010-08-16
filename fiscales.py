# -*- coding: iso-8859-1 -*-
#/****************************************************************************
#* 
#* Andres Hocevar 2010-2011
#*
#* fiscales.py 
#* licencia GPL v3
#* Clase que permite enviar comandos a impresoras fiscales
#*          http://code.google.com/p/factfis
#***************************************************************************/

import serial
import operator
import sys
import time
import glob

class factfis:
	bandera=False
	mdepura=False
	puerto =None
	status =''
	error  =''
	envio  =''
	status =''
	error  =''

	def __init__(self,p='auto'):
		if p=='auto':
			posibles=glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*')
			for self.puerto in posibles:
				if self.OpenFpctrl():
					if self.ManipulaCTS_RTS():
						self._write(chr(0x05))
						time.sleep(0.2)
						t=self.ser.inWaiting()
						if t>0:
							self.ser.setRTS(False)
							break
					else:
						self.CloseFpctrl()
		else:
			self.puerto = p

	def OpenFpctrl(self):
		if not self.bandera:
			try:
				self.ser = serial.Serial(
				port=self.puerto,
				baudrate=9600,
				bytesize=serial.EIGHTBITS,
				parity  =serial.PARITY_EVEN,
				stopbits=serial.STOPBITS_ONE,
				timeout =1.5,
				writeTimeout=5,
				xonxoff=0,
				rtscts=0) 
				self.bandera=True
				return True
			except serial.SerialException:
				self.bandera=False
				self.envio = "Impresora no conectada o error accediendo al puerto"
				return False

	def CloseFpctrl(self):
		if self.bandera:
			self.ser.close()
			self.bandera=False

	def ManipulaCTS_RTS(self):
		try:
			self.ser.setRTS(True)
			lpri=1
			while not self.ser.getCTS():
				time.sleep(lpri/10)
				lpri=lpri+1
				if lpri>20:
					self.ser.setRTS(False)
					return False
			return True
		except serial.SerialException:
			return False

	def SimpleCmd(self,cmd):
		try:
			self.ser.flushInput()
			self.ser.flushOutput()
			if self.ManipulaCTS_RTS():
				msj=self.qenviar(cmd)
				self._write(msj)
				rt=self._read(1)
				if rt==chr(0x06):
					self.envio = "Status: 00  Error: 00"
					rt=True
				else:
					self.envio = "Status: 00  Error: 89"
					rt=False
			else:
				self.DarStatus_Error(0, 128);
				self.envio = "Error... CTS in False"
				rt=False
			self.ser.setRTS(False)
		except serial.SerialException:
			rt=False
		return rt

	def QueryCmd(self,cmd):
		try:
			self.ser.flushInput()
			self.ser.flushOutput()
			if self.ManipulaCTS_RTS():
				msj=self.qenviar(cmd)
				self._write(msj)
				rt=True
			else:
				self.DarStatus_Error(0, 128);
				self.envio = "Error... CTS in False"
				rt=False
			self.ser.setRTS(False)
		except serial.SerialException:
			rt=False
		return rt

	def FecthRow(self):
		while True:
			time.sleep(0.7)
			bytes = self.ser.inWaiting()
			if bytes>3:
				msj=self._read(bytes)
				linea=msj[1:-1]
				lrc=chr(self.lrc(linea))
				if lrc==msj[-1]:
					self.ser.flushInput()
					self.ser.flushOutput()
					self._write(chr(0x06))
					return msj
				else:
					self._write(chr(0x15))
			else:
				break
		return None


	def ReadFpStatus(self):
		if self.ManipulaCTS_RTS():
			msj=chr(0x05)
			self._write(msj)
			time.sleep(0.05)
			#bytes = self.ser.inWaiting()
			r=self._read(5)
			if len(r)==5:
				if ord(r[1])^ord(r[2])^0x03 == ord(r[4]):
					return self.DarStatus_Error(ord(r[1]), ord(r[2]))
				else:
					return self.DarStatus_Error(0, 144)
			else:
				self.estado = "Impresora ocupada";
				return self.DarStatus_Error(0, 114)
		else:
			return self.DarStatus_Error(0, 128);
			self.estado = "Error... CTS in False";

	def _write(self,msj):
		if self.mdepura:
			print '<<< '+self.depura(msj)
		self.ser.write(msj)

	def _read(self,bytes):
		msj = self.ser.read(bytes)
		if self.mdepura:
			print '>>> '+self.depura(msj)
		return msj

	def qenviar(self,linea):
		lrc = self.lrc(linea+chr(0x03))
		previo=chr(0x02)+linea+chr(0x03)+chr(lrc)
		return previo

	def lrc(self,linea):
		return reduce(operator.xor, map(ord, linea))

	def depura(self,linea):
		if linea!=None:
			if len(linea)==0:
				return 'null'
			if len(linea)>3:
				lrc=linea[-1]
				linea=linea[0:-1]
				adic=' LRC('+str(ord(lrc))+')'
			else:
				adic=''
			linea=linea.replace(chr(0x02),'STX',1)
			linea=linea.replace(chr(0x05),'ENQ',1)
			linea=linea.replace(chr(0x03),'ETX',1)
			linea=linea.replace(chr(0x04),'EOT',1)
			linea=linea.replace(chr(0x06),'ACK',1)
			linea=linea.replace(chr(0x15),'NAK',1)
			linea=linea.replace(chr(0x17),'ETB',1)

		return linea+adic

	def estado1(self):
		if self.QueryCmd('S1'):
			msj=1
			while True:
				msj=self.FecthRow()
				if msj==None:
					break
				msj=msj[1:-2]
				m=msj.split(chr(10))
				if len(m)>=9:
					return m
		return None

	def DarStatus_Error(self,st,er):
		st_aux = st;
		st = st & ~0x04

		if   (st & 0x6A) == 0x6A: #En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos no fiscales
			self.status='En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos no fiscales'
			status = "12"
		elif (st & 0x69) == 0x69: #En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos  fiscales
			self.status='En modo fiscal, carga completa de la memoria fiscal y emisi�n de documentos  fiscales'
			status = "11"
		elif (st & 0x68) == 0x68: #En modo fiscal, carga completa de la memoria fiscal y en espera
			self.status='En modo fiscal, carga completa de la memoria fiscal y en espera'
			status = "10"
		elif (st & 0x72) == 0x72: #En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales
			self.status='En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales'
			status = "9 "
		elif (st & 0x71) == 0x71: #En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales
			self.status='En modo fiscal, cercana carga completa de la memoria fiscal y en emisi�n de documentos no fiscales'
			status = "8 "
		elif (st & 0x70) == 0x70: #En modo fiscal, cercana carga completa de la memoria fiscal y en espera
			self.status='En modo fiscal, cercana carga completa de la memoria fiscal y en espera'
			status = "7 "
		elif (st & 0x62) == 0x62: #En modo fiscal y en emisi�n de documentos no fiscales
			self.status='En modo fiscal y en emisi�n de documentos no fiscales'
			status = "6 "
		elif (st & 0x61) == 0x61: #En modo fiscal y en emisi�n de documentos fiscales
			self.status='En modo fiscal y en emisi�n de documentos fiscales'
			status = "5 "
		elif (st & 0x60) == 0x60: #En modo fiscal y en espera
			self.status='En modo fiscal y en espera'
			status = "4 "
		elif (st & 0x42) == 0x42: #En modo prueba y en emisi�n de documentos no fiscales
			self.status='En modo prueba y en emisi�n de documentos no fiscales'
			status = "3 "
		elif (st & 0x41) == 0x41: #En modo prueba y en emisi�n de documentos fiscales
			self.status='En modo prueba y en emisi�n de documentos fiscales'
			status = "2 "
		elif (st & 0x40) == 0x40: #En modo prueba y en espera
			self.status='En modo prueba y en espera'
			status = "1 "
		elif (st & 0x00) == 0x00: #Status Desconocido
			self.status='Status Desconocido'
			status = "0 "

		if   (er & 0x6C) == 0x6C: #Memoria Fiscal llena
			self.error = 'Memoria Fiscal llena'
			error = "108"
		elif (er & 0x64) == 0x64: #Error en memoria fiscal
			self.error = 'Error en memoria fiscal'
			error = "100"
		elif (er & 0x60) == 0x60: #Error Fiscal
			self.error = 'Error Fiscal'
			error = "96 "
		elif (er & 0x5C) == 0x5C: #Comando Invalido
			self.error = 'Comando Invalido'
			error = "92 "
		elif (er & 0x58) == 0x58: # No hay asignadas  directivas
			self.error = 'No hay asignadas  directivas'
			error = "88 "
		elif (er & 0x54) == 0x54: #Tasa Invalida
			self.error = 'Tasa Invalida'
			error = "84 "
		elif (er & 0x50) == 0x50: #Comando Invalido/Valor Invalido
			self.error = 'Comando Invalido/Valor Invalido'
			error = "80 "
		elif (er & 0x43) == 0x43: #Fin en la entrega de papel y error mec�nico
			self.error = 'Fin en la entrega de papel y error mec�nico'
			error = "3  "
		elif (er & 0x42) == 0x42: #Error de indole mecanico en la entrega de papel
			self.error = 'Error de indole mecanico en la entrega de papel'
			error = "2  "
		elif (er & 0x41) == 0x41: #Fin en la entrega de papel
			self.error = 'Fin en la entrega de papel'
			error = "1  "
		elif (er & 0x40) == 0x40: #Sin error
			self.error = 'Sin error'
			error = "0  "

		if (st_aux & 0x04) == 0x04: #Buffer Completo
			self.error = ''
			error = "112 "
		elif er == 128:     # Error en la comunicacion
			self.error = 'CTS en falso'
			error = "128 ";
		elif er == 137:     # No hay respuesta
			self.error = 'No hay respuesta'
			error = "137 ";
		elif er == 144:     # Error LRC
			self.error = 'Error LRC'
			error = "144 ";
		elif er == 114:
			self.error = 'Impresora no responde o ocupada'
			error = "114 ";


		return status+"   "+error


#imp=factfis()
#h=imp.qenviar('pelusa')
#print imp.depura(h)
#j=imp.DarStatus_Error(0,112);
#print j

"""
	def reiniciar(self):
		if self.bandera:
			self.ser.close()
			self.ser.open()

	def qenviar(self,linea):
		lrc = reduce(operator.xor, map(ord, linea+chr(03)))
		previo=chr(02)+linea+chr(03)+chr(lrc)
		return previo

	def qrecibe(self,linea):
		stl1 = den2bin.Denary2Binary(linea[1:2])
		stl2 = den2bin.Denary2Binary(linea[2:3])
		stl3 = linea[3:4]
		return [stl1,stl2]

	def qcheck(self,linea):
		if len(linea)==5:
			lrc = reduce(operator.xor, map(ord, linea[1:3]+chr(03)))
			if chr(lrc)==linea[4]:
				return 1
			else:
				print 'Error de LRC'
			exit
		elif len(linea)==1 and linea==chr(06):
			return 1
		return 0

	#  0 para repetir envio (error no grave o desconocido)
	#  1 sin errores
	# -1 error grave
	# -2 impresora no responde
	def qstatus(self,linea):
		if len(linea)==0:
			print 'Respuesta nula'
			return -2

		if linea==chr(6):
			print 'Respuesta 6 Todo bien'
			return 1

		if len(linea)<2:
			print 'Respuesta corta'
			return 0

		control=0
		stl=self.qrecibe(linea)
		if len(stl[0])==7 and len(stl[1])==7:
			if stl[0][6]=='1':
				print 'En transaccion fiscal'
			if stl[0][5]=='1':
				print 'En transaccion NO fiscal'
			if stl[0][4]=='1':
				print 'Ocupado buffer lleno'
			if stl[0][3]=='1':
				print 'Memoria fiscal llena'
				control=-1
			if stl[0][2]=='1' and control!=-1:
				print 'Memoria fiscal aproximandamente llena'
			if stl[0][1]=='1' and control!=-1:
				#control=1
				print 'Modo fiscal'
			if stl[1][6]=='1' and control!=-1:
				control=-1
				print 'Fin del papel'
			if stl[1][5]=='1' and control!=-1:
				control=-1
				print 'Error de impresora o visor'
			if stl[1][:5]=='11100' and control!=-1:
				control=-1
				print 'La fecha no ha sido programada aun'
			if stl[1][:5]=='11011' and control!=-1:
				control=-1
				print 'Memoria Fiscal llena'
			if stl[1][:5]=='11001' and control!=-1:
				control=-1
				print 'Error de memoria fiscal'
			if stl[1][:5]=='11000' and control!=-1:
				control=-1
				print 'Error fiscal'
			if stl[1][:5]=='10111' and control!=-1:
				control=2
				print 'Comando invalido / Formato de comando errado'
			if stl[1][:5]=='10110' and control!=-1:
				print 'Sin cajero asignado'
			if stl[1][:5]=='10101' and control!=-1:
				print 'Impuesto invalido'
			if stl[1][:5]=='10100' and control!=-1:
				print 'Valor invalido / desbordamiento de memoria'
			if stl[1]=='1000000' and control!=-1:
				control=1
				print 'Sin Error'
		else:
			control=2
			print 'Error de respuesta de la impresora', stl
		return control

	def leer(self):
		lpri=1
		while 1:
			responde = self.ser.read()
			if len(responde)>0:
				break
			elif lpri>10:
				print 'impresora no responde'
				return None
			else:
				lpri=lpri+1
				time.sleep(lpri/10)
		restanby = self.ser.inWaiting()
		if restanby>0:
			restantes=self.ser.read(restanby)
			responde=responde+restantes
		print '<<<',responde,map(ord, responde)
		return responde
	
	def escribir(self,previo):
		previo=self.qenviar(previo)
		i=0
		respuesta=chr(5)
		while respuesta<>chr(15):
			self.ser.write(previo)
			print '>>>',previo
			time.sleep(0.4)
			respuesta=self.leer();
			if respuesta==chr(06):
				return 1
			if i>49 or respuesta==None:
				break
			i=i+1
			#self.ser.write(chr(06))
			#print '>>> Pide Status'
			#respuesta=self.leer();
			#self.estatus=self.qstatus(respuesta);
		return 0


	def __del__(self):
		if self.bandera:
			self.ser.close()
"""