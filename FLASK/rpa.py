from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def build_message(customer, vehicle):
    return f"""Estimado/a {customer.name},

Le informamos que su vehículo ha ingresado en el proceso de: {vehicle.status}.

Comentario: {vehicle.comentario}

Quedamos a su disposición,
Tecnicar Autoservices"""

def send_whatsapp_message(phone_number, message):
    # Configurar opciones del navegador
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    # Crear instancia del navegador
    driver = webdriver.Chrome(options=options)

    try:
        wait = WebDriverWait(driver, 60)  # Aumentar el tiempo de espera a 60 segundos

        # Navega a la conversación del contacto
        driver.get(f"https://web.whatsapp.com/send?phone={phone_number}")

        # Pausa para asegurar que la página se actualice completamente
        time.sleep(10)

        # Espera hasta que el campo de entrada del mensaje esté presente
        message_box = wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
        )

        # Envía el mensaje parte por parte
        for part in message.split('\n'):
            message_box.send_keys(part)
            message_box.send_keys(Keys.SHIFT + Keys.ENTER)

        # Envía el mensaje
        message_box.send_keys(Keys.ENTER)

        print("Mensaje enviado con éxito.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        driver.quit()