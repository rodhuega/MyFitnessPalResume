from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest
import time
import re
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import datetime
import json
import os
import copy
import locale
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import smtplib
from fpdf import FPDF
import PyPDF2
import base64


class CustomConfiguration:

        def __init__(self, user, password, IsNecessaryLogin, IsFacebookLogin,IsPDF, chromeProfile, customLocale, emailSender, emailPassword,emails):
                self.user = user
                self.password = password
                self.IsNecessaryLogin = IsNecessaryLogin
                self.IsFacebookLogin = IsFacebookLogin
                self.IsPDF=IsPDF
                self.chromeProfile = chromeProfile
                self.customLocale = customLocale
                self.emailSender = emailSender
                self.emailPassword=emailPassword
                self.emails = emails


class Alimento:

        def __init__(self, nombre, cantidad, unidades):
                self.nombre = nombre
                self.cantidad = cantidad
                self.unidades = unidades

        def agregarCantidad(self, cantidadASumar):
                self.cantidad += cantidadASumar

        def __repr__(self):
                res = self.nombre + ": " + \
                    str(self.cantidad) + " " + self.unidades
                return res

#estructura [{"nombre":alimento}]
alimentosConCantitdadTotal = {}
urlBaseDiario = "https://www.myfitnesspal.com/es/food/diary?date="
driver = None
cc = None
#[{fecha,dia}]
dias = {}


def ConseguirDatosEntreFechas(inicial, final):
        global driver, dias
        actual = inicial
        while(actual <= final):
                fechaEnTexto = actual.strftime("%Y-%m-%d")
                urlNueva = urlBaseDiario+fechaEnTexto
                driver.get(urlNueva)
                dia = AlimentosDeUnDia()
                dias[actual] = dia
                actual = actual+datetime.timedelta(days=1)


def AlimentosDeUnDia():
        global driver, alimentosConCantitdadTotal
        filas = driver.find_elements_by_tag_name("tr")
        comidasDelDia = {}
        comida = {}
        nombreComida = ""
        for fila in filas:
                if fila.get_attribute("class") == "meal_header":
                        if nombreComida != "":
                                comidasDelDia[nombreComida] = comida
                                comida = {}
                        nombreComida = fila.find_elements_by_tag_name(
                            "td")[0].get_attribute("innerHTML")
                else:
                        try:
                                alimento = fila.find_element_by_class_name(
                                    "js-show-edit-food")
                                textoAlimento = alimento.get_attribute(
                                    'innerHTML')
                                posicionSeparadora = textoAlimento.rfind(",")
                                nombreAlimento, cantidadAlimentoConUnidades = textoAlimento[:posicionSeparadora].lstrip(
                                ), textoAlimento[posicionSeparadora+1:].lstrip()
                                posicionSeparadoraUnidades = cantidadAlimentoConUnidades.find(
                                    " ")
                                soloCantidad, soloUnidades = cantidadAlimentoConUnidades[:posicionSeparadoraUnidades].lstrip(
                                ), cantidadAlimentoConUnidades[posicionSeparadoraUnidades+1:].lstrip()
                                soloUnidades=soloUnidades.rstrip()
                                auxAlimento = Alimento(nombreAlimento, float(
                                    soloCantidad), soloUnidades)
                                alimentoRecuperado = comida.get(nombreAlimento)
                                #dentro de la propia comida
                                if alimentoRecuperado != None:
                                        alimentoRecuperado.agregarCantidad(
                                            auxAlimento.cantidad)
                                else:
                                        comida[nombreAlimento] = auxAlimento
                                #en la lista de la compra
                                alimentoRecuperadoListaGeneral = alimentosConCantitdadTotal.get(
                                    nombreAlimento)
                                if alimentoRecuperadoListaGeneral != None:
                                        alimentoRecuperadoListaGeneral.agregarCantidad(
                                            auxAlimento.cantidad)
                                else:
                                        alimentosConCantitdadTotal[nombreAlimento] = copy.copy(
                                            auxAlimento)
                        except NoSuchElementException:
                                pass
        comidasDelDia[nombreComida] = comida
        return comidasDelDia


def loadJson(path):
        with open(path) as f:
                data = json.load(f)
                cc = CustomConfiguration(**data)
        return cc


def saveJson(path, objectToSave):
        with open(path, "w") as f:
                jsonText = json.dumps(objectToSave.__dict__)
                f.write(jsonText)


def loginToFacebook():
        global driver, cc
        driver.get("https://www.facebook.com/?stype=lo&jlou=AfciIfCXUHokOG6Qxtvu5niV4Nf2OAxyC1rGvD_tGP5iq8Iw6OvEtte9MstKY5BPGI8DRHcGzAmwcEZ55-NBGmjw&smuh=14792&lh=Ac8QBwhrXgJbf7fJ")
        driver.find_element_by_id("email").click()
        driver.find_element_by_id("email").clear()
        driver.find_element_by_id("email").send_keys(cc.user)
        driver.find_element_by_id("pass").clear()
        driver.find_element_by_id("pass").send_keys(cc.password)
        driver.find_element_by_id("loginbutton").click()

def resumenString(inicial, final):
        global alimentosConCantitdadTotal, dias
        res=f'Información conmida del {inicial.strftime("%A %d-%m-%Y")} al {final.strftime("%A %d-%m-%Y")}\n'
        res+="Información de cada comida: "
        for dia in dias.keys():
                res+=f'Dia {dia.strftime("%A %d-%m-%Y")}\n'
                comidasDeEseDia=dias[dia]
                for comidaActual in comidasDeEseDia.keys():
                        res+=f"\t{comidaActual}\n"
                        alimentosComidaActual = comidasDeEseDia[comidaActual]
                        for alimiento in alimentosComidaActual.keys():
                                res+="\t\t"+str(alimentosComidaActual[alimiento])+"\n"
        res+="\n\nInformación para la lista de la compra\n"
        for alimento in alimentosConCantitdadTotal.keys():
                res+="\t"+str(alimentosConCantitdadTotal[alimento])+"\n"
        return res

def resumenPDF(inicial, final):
        global alimentosConCantitdadTotal, dias,cc
        pdf=FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", size=15,style='B')
        textoAEscribir=f'Información comida del {inicial.strftime("%A %d-%m-%Y")} al {final.strftime("%A %d-%m-%Y")}'
        pdf.cell(200, 10, txt=textoAEscribir, ln=1, align="C")
        textoAEscribir="Información de cada comida: "
        pdf.set_font("Arial", size=12,style='B')
        pdf.cell(200, 10, txt=textoAEscribir, ln=2, align="C")
        i=3
        for dia in dias.keys():
                textoAEscribir=f'{dia.strftime("%A %d-%m-%Y")}\n'
                pdf.set_font("Arial", size=10,style='B')
                pdf.cell(200, 10, txt=textoAEscribir, ln=i)
                i+=1
                comidasDeEseDia=dias[dia]
                for comidaActual in comidasDeEseDia.keys():
                        textoAEscribir=f"\t{comidaActual}"
                        pdf.set_font("Arial", size=10)
                        pdf.set_text_color(255,0,0)
                        pdf.cell(200, 10, txt=textoAEscribir, ln=i)
                        pdf.set_text_color(0,0,0)
                        i+=1
                        alimentosComidaActual = comidasDeEseDia[comidaActual]
                        for alimiento in alimentosComidaActual.keys():
                                textoAEscribir="\t\t"+str(alimentosComidaActual[alimiento])
                                pdf.set_font("Arial", size=8)
                                pdf.cell(200, 10, txt=textoAEscribir, ln=i)
                                i+=1
        textoAEscribir="Información para la lista de la compra"
        pdf.set_font("Arial", size=12,style='B')
        pdf.cell(200, 10, txt=textoAEscribir, ln=i+2)
        i+=1
        for alimento in alimentosConCantitdadTotal.keys():
                textoAEscribir="\t"+str(alimentosConCantitdadTotal[alimento])
                pdf.set_font("Arial", size=8,)
                pdf.cell(200, 10, txt=textoAEscribir, ln=i)
                i+=1
        i+=1
        return pdf.output(dest="S").encode("latin-1")
def sendEmail(inicial, final):
        global cc
        # create message object instance
        
        
        msg = MIMEMultipart()
        
        # setup the parameters of the message
        msg['From'] = cc.emailSender
        msg['To'] = cc.emails
        msg['Subject'] = f'Información comidas del: {inicial.strftime("%d-%m-%Y")} al {final.strftime("%d-%m-%Y")}'
        
        # add in the message body
        if cc.IsPDF:
            stringPdf = resumenPDF(inicial, final)
            msg.attach(MIMEApplication(stringPdf,Name="informacion.pdf",_subtype="pdf"))
        else:
            message = resumenString(inicial, final)
            msg.attach(MIMEText(message, 'plain'))
        
        # create server
        server = smtplib.SMTP('smtp.gmail.com: 587')
        
        server.starttls()
        
        # Login Credentials for sending the mail
        server.login(msg['From'], cc.emailPassword)
        
        
        # send the message via the server.
        server.sendmail(msg['From'], msg['To'].split(", "), msg.as_string())
        
        server.quit()


def main():
        global driver, alimentosConCantitdadTotal,cc

        cc = loadJson(os.path.dirname(os.path.abspath(
            __file__))+"/configuration.json")
        locale.setlocale(locale.LC_ALL, cc.customLocale)
        print("Fechas en estructura año-mes-dia, año 4 digitos, mes y dia 2 digitos")
        fechaInicialTexto = input("Introduzca la fecha inicial: ")
        fechaFinalTexto = input("Introduzca la fecha Final: ")
        fechaInicialArray = fechaInicialTexto.split("-")
        fechaFinalArray = fechaFinalTexto.split("-")
        fechaInicial = datetime.datetime(int(fechaInicialArray[0]), int(
            fechaInicialArray[1]), int(fechaInicialArray[2]))
        fechaFinal = datetime.datetime(int(fechaFinalArray[0]), int(
            fechaFinalArray[1]), int(fechaFinalArray[2]))

        options = Options()
        options.add_argument("user-data-dir=" + cc.chromeProfile)
        driver = webdriver.Chrome(
            ChromeDriverManager().install(), chrome_options=options)

        if cc.IsNecessaryLogin:
                if cc.IsFacebookLogin:
                        loginToFacebook()
                        driver.get(
                            "https://www.myfitnesspal.com/es/account/login")
                        time.sleep(2)
                        driver.switch_to.frame(1)
                        # ERROR: Caught exception [ERROR: Unsupported command [selectFrame | relative=parent | ]]
                        # ERROR: Caught exception [ERROR: Unsupported command [selectFrame | index=2 | ]]
                        driver.find_element_by_css_selector(
                            "#u_0_1 > div > table > tbody > tr > td:nth-child(2) > div > div").click()
                        time.sleep(3)
                else:
                        driver.get(
                            "https://www.myfitnesspal.com/es/account/login")

        ConseguirDatosEntreFechas(fechaInicial, fechaFinal)

        # ERROR: Caught exception [ERROR: Unsupported command [selectWindow | win_ser_1 | ]]
        sendEmail(fechaInicial,fechaFinal)
        driver.close()


if __name__ == "__main__":
    main()
