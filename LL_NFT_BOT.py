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
import asyncio

TELEGRAM_TOKEN = 'TOKEN_TELEGRAM'

# Variabile prezzo
desired_prices = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "Benvenuto al bot di notifica degli NFT dei LL! 🎉\n"
        "Per iniziare, ti chiedo di impostare un prezzo massimo per i LL.\n"
        "Usa il comando /setprice seguito da un valore numerico. Esempio: /setprice 500 \n"
        "Questo imposterà il tuo prezzo di interesse a $500 e riceverai notifiche per gli NFT listati al di sotto di questo prezzo."
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
            # Chiama subito la funzione per controllare nuovi NFT listati
            await scrape_nfts(chat_id, price, context)
        except ValueError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Per favore, inserisci un numero valido.")
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


    wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, 'a.css-1rdp2dl')))
    link_elements = driver.find_elements(By.CSS_SELECTOR, 'a.css-1rdp2dl')

    messages = []
    for link_element in link_elements[:5]:  # Controlla solo i primi 5 per efficienza
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
