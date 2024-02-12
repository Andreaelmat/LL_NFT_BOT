from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re
import time
import asyncio

TELEGRAM_TOKEN = 'TELEGRAM_TOKEN'

desired_prices = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "Benvenuto al bot di notifica degli NFT! 🎉\n"
        "Per iniziare, imposta un prezzo massimo per gli NFT che ti interessano con /setprice."
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message)

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) == 1:
        try:
            price = float(args[0])
            chat_id = update.effective_chat.id
            desired_prices[chat_id] = {'price': price, 'nfts': []}
            await context.bot.send_message(chat_id=chat_id, text=f"Il prezzo è stato impostato a: ${price}. Vedrai subito gli ultimi list e poi aggiornato ogni 5 minuti!")
            await scrape_nfts(chat_id, price, context)
        except ValueError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Inserisci un numero valido.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usa: /setprice <prezzo>")

async def scrape_nfts(chat_id: int, price_limit: float, context: ContextTypes.DEFAULT_TYPE):
    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1200")
    DRIVER_PATH = './chromedriver'

    driver = webdriver.Chrome(options=options, service=Service(DRIVER_PATH))
    driver.get("https://crypto.com/nft/collection/82421cf8e15df0edcaa200af752a344f?tab=activity")

    wait = WebDriverWait(driver, 20)

    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="onetrust-accept-btn-handler"]'))).click()
    except TimeoutException:
        print("Il pulsante per accettare i cookie non è stato trovato o non è necessario cliccarlo.")

    # Implementazione dello scrolling infinito
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # Attendi che la pagina carichi
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    link_elements = driver.find_elements(By.CSS_SELECTOR, 'a.css-1rdp2dl')
    messages = []
    for link_element in link_elements[:5]:  # Limita a 5 
        try:
            title_element = link_element.find_element(By.CLASS_NAME, 'css-cd6wvw')
            price_element = link_element.find_element(By.CLASS_NAME, 'css-15y6ahk')
            title_text = title_element.text.strip()
            price_text = re.sub(r'[^\d.]', '', price_element.text.strip())
            if 'K' in price_element.text.strip():
                price_value = float(price_text) * 1000
            else:
                price_value = float(price_text)
            if price_value <= price_limit:
                link_url = link_element.get_attribute('href')
                messages.append(f"{title_text} Prezzo List: ${price_value} - Link: {link_url}")
        except Exception as e:
            print(f"Errore durante lo scraping di un elemento: {e}")

    driver.quit()

    if messages:
        await context.bot.send_message(chat_id=chat_id, text="\n".join(messages))
    else:
        await context.bot.send_message(chat_id=chat_id, text="Nessun NFT trovato sotto il prezzo impostato.")

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setprice", set_price))

    application.run_polling()

if __name__ == '__main__':
    main()

