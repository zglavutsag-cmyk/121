import os

TOKEN = os.getenv('TOKEN')
GROUP_ID = int(os.getenv('GROUP_ID', 0))
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', 0))
EXCHANGE_RATE = int(os.getenv('EXCHANGE_RATE', 10))

NOTIFY_FARM_THRESHOLD = 50  # Уведомлять при накоплении 50+ монет
# ==================================

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

temp_referrals = {}
temp_purchases = {}
user_withdraw_requests = {}
user_discounts = {}  # Хранилище скидок для пользователей
last_notify_time = {}  # Время последнего уведомления о фарме

# ---------- КЛАВИАТУРЫ ----------
def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('⛏ Фарм', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('📊 Мой профиль', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('💰 Вывод', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('🛒 Купить карты', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('📋 Моя ферма', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('👑 Топ игроков', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('🤝 Рефералы', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('❓ Помощь', color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_cards_shop_keyboard():
    keyboard = VkKeyboard(one_time=False)
    cards = get_all_cards()
    row_count = 0
    for card in cards:
        card_id, name, rate, price_rub, desc, emoji, min_ref = card
        if price_rub > 0:
            button_text = f"{emoji} {name} | {price_rub} ₽"
            keyboard.add_button(button_text, color=VkKeyboardColor.PRIMARY)
            row_count += 1
            if row_count >= 2:
                keyboard.add_line()
                row_count = 0
    if row_count > 0:
        keyboard.add_line()
    keyboard.add_button('◀️ Назад', color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_payment_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('✅ Я оплатил', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_welcome_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('▶️ Начать игру', color=VkKeyboardColor.POSITIVE)
    return keyboard

def get_withdraw_amount_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('1250', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('2500', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('5000', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('10000', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('25000', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('50000', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('100000', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('◀️ Назад', color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_withdraw_cancel_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.NEGATIVE)
    return keyboard

def get_admin_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('📋 Заявки на вывод', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('🛒 Заявки на покупку', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('💰 Выдать монеты', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('🖥 Выдать карту', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('🎁 Скидка для игрока', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('📊 Статистика бота', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('📢 Рассылка', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('◀️ Назад', color=VkKeyboardColor.NEGATIVE)
    return keyboard

# ---------- БАЗА ДАННЫХ ----------
def init_db():
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        last_claim TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_earned INTEGER DEFAULT 0,
        total_withdrawn INTEGER DEFAULT 0,
        referrer_id INTEGER DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    try:
        c.execute('ALTER TABLE users ADD COLUMN total_withdrawn INTEGER DEFAULT 0')
    except: pass
    try:
        c.execute('ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT NULL')
    except: pass
    try:
        c.execute('ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    except: pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        card_id INTEGER,
        quantity INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (card_id) REFERENCES cards(id),
        UNIQUE(user_id, card_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY,
        name TEXT,
        rate_per_hour REAL,
        price_rub INTEGER,
        description TEXT,
        emoji TEXT,
        min_referrals INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        rub_amount INTEGER,
        card_number TEXT,
        phone TEXT,
        bank TEXT,
        full_name TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        card_id INTEGER,
        amount_rub INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM cards")
    if c.fetchone()[0] == 0:
        cards = [
            (1, 'GT 710', 1, 195, '🐢 Начальная карта', '🐢', 0),
            (2, 'GT 1030', 2, 295, '📀 Бюджетный вариант', '📀', 0),
            (3, 'RX 570', 4, 395, '🎮 Уже можно играть', '🎮', 0),
            (4, 'GTX 1660 Super', 7, 495, '⚡ Хороший выбор', '⚡', 0),
            (5, 'RTX 3060', 10, 595, '🔥 Популярная карта', '🔥', 0),
            (6, 'RTX 4070', 15, 696, '💎 Современная мощность', '💎', 0),
            (7, 'RTX 4090', 30, 795, '👑 Флагман NVIDIA', '👑', 0),
            (8, 'RX 7900 XTX', 40, 999, '🚀 Флагман AMD', '🚀', 0),
            (9, 'Секретная карта', 5, 0, '🌟 Выдаётся за 5 приглашённых друзей', '🌟', 5)
        ]
        c.executemany("INSERT INTO cards (id, name, rate_per_hour, price_rub, description, emoji, min_referrals) VALUES (?,?,?,?,?,?,?)", cards)
        conn.commit()
    
    conn.close()

init_db()

# ---------- ФУНКЦИИ ----------
def send_msg(user_id, text, keyboard=None):
    try:
        if keyboard:
            vk.messages.send(user_id=user_id, message=text, random_id=random.randint(1, 2**31), keyboard=keyboard.get_keyboard())
        else:
            vk.messages.send(user_id=user_id, message=text, random_id=random.randint(1, 2**31))
    except Exception as e:
        print(f"Ошибка отправки {user_id}: {e}")

def send_to_admin_chat(text):
    try:
        vk.messages.send(peer_id=ADMIN_CHAT_ID, message=text, random_id=random.randint(1, 2**31))
    except Exception as e:
        print(f"Ошибка отправки в админ-чат: {e}")

def is_admin(user_id):
    return user_id in ADMIN_IDS

def check_subscribe(user_id):
    try:
        members = vk.groups.getMembers(group_id=GROUP_ID, count=1000)
        if user_id in members['items']:
            return True
        total = members['count']
        if total > 1000:
            for offset in range(1000, total, 1000):
                next_members = vk.groups.getMembers(group_id=GROUP_ID, count=1000, offset=offset)
                if user_id in next_members['items']:
                    return True
        return False
    except Exception as e:
        print(f"Ошибка проверки подписки {user_id}: {e}")
        return False

def get_user_balance(user_id):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_total_rate(user_id):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('''SELECT SUM(cards.rate_per_hour * user_cards.quantity)
                 FROM user_cards
                 JOIN cards ON user_cards.card_id = cards.id
                 WHERE user_cards.user_id = ?''', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else 0

def get_user_cards(user_id):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('''SELECT cards.id, cards.name, cards.rate_per_hour, cards.emoji, user_cards.quantity
                 FROM user_cards
                 JOIN cards ON user_cards.card_id = cards.id
                 WHERE user_cards.user_id = ? AND user_cards.quantity > 0
                 ORDER BY cards.id''', (user_id,))
    cards = c.fetchall()
    conn.close()
    return cards

def get_user_data(user_id):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('SELECT balance, last_claim, total_earned, total_withdrawn, referrer_id, created_at FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    balance, last_claim_str, total_earned, total_withdrawn, referrer_id, created_at_str = row
    last_claim = datetime.fromisoformat(last_claim_str)
    created_at = datetime.fromisoformat(created_at_str)
    total_rate = get_total_rate(user_id)
    return (balance, last_claim, total_earned, total_withdrawn, referrer_id, created_at, total_rate)

def update_user_data(user_id, balance, last_claim, total_earned=None):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    if total_earned is not None:
        c.execute('UPDATE users SET balance = ?, last_claim = ?, total_earned = ? WHERE user_id = ?',
                  (balance, last_claim.isoformat(), total_earned, user_id))
    else:
        c.execute('UPDATE users SET balance = ?, last_claim = ? WHERE user_id = ?',
                  (balance, last_claim.isoformat(), user_id))
    conn.commit()
    conn.close()

def update_withdrawn(user_id, total_withdrawn):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('UPDATE users SET total_withdrawn = ? WHERE user_id = ?', (total_withdrawn, user_id))
    conn.commit()
    conn.close()

def add_card_to_user(user_id, card_id, quantity=1):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    
    c.execute('SELECT quantity FROM user_cards WHERE user_id = ? AND card_id = ?', (user_id, card_id))
    row = c.fetchone()
    
    if row:
        new_quantity = row[0] + quantity
        c.execute('UPDATE user_cards SET quantity = ? WHERE user_id = ? AND card_id = ?', 
                  (new_quantity, user_id, card_id))
    else:
        c.execute('INSERT INTO user_cards (user_id, card_id, quantity) VALUES (?, ?, ?)',
                  (user_id, card_id, quantity))
    
    conn.commit()
    conn.close()

def register_user(user_id, referrer_id=None):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    
    c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    exists = c.fetchone()
    
    if exists:
        conn.close()
        return False, None
    
    now_str = datetime.now().isoformat()
    
    c.execute('''INSERT INTO users (user_id, balance, last_claim, total_earned, total_withdrawn, referrer_id, created_at) 
                 VALUES (?, 0, ?, 0, 0, ?, ?)''',
              (user_id, now_str, referrer_id, now_str))
    
    add_card_to_user(user_id, 1, 1)
    
    conn.commit()
    conn.close()
    
    if referrer_id and referrer_id != user_id:
        referrer_balance = get_user_balance(referrer_id)
        if referrer_balance is not None:
            new_balance = referrer_balance + 10
            conn = sqlite3.connect('farm.db')
            c = conn.cursor()
            c.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, referrer_id))
            conn.commit()
            conn.close()
            
            # Уведомление о реферальном бонусе
            try:
                user_info = vk.users.get(user_ids=user_id)[0]
                friend_name = f"{user_info['first_name']} {user_info['last_name']}"
            except:
                friend_name = "Новый игрок"
            
            send_msg(referrer_id, f"🤝 РЕФЕРАЛЬНЫЙ БОНУС!\n━━━━━━━━━━━━━━━\n👤 {friend_name} присоединился по вашей ссылке!\n💰 Вы получили +10 GPcoin!\n━━━━━━━━━━━━━━━\n🔥 Осталось пригласить друзей до секретной карты: {5 - get_referral_stats(referrer_id)}", get_main_keyboard())
            
            conn = sqlite3.connect('farm.db')
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (referrer_id,))
            friends_count = c.fetchone()[0]
            conn.close()
            
            if friends_count >= 5:
                add_card_to_user(referrer_id, 9, 1)
                send_msg(referrer_id, "🌟 ПОЗДРАВЛЯЕМ! 🌟\n━━━━━━━━━━━━━━━\nВы пригласили 5 друзей!\n🎁 Вам выдана СЕКРЕТНАЯ КАРТА!\n⚡ Скорость: 5 GPcoin/час\n━━━━━━━━━━━━━━━\nТеперь ваша ферма стала ещё мощнее! 🚀", get_main_keyboard())
            
            return True, referrer_id
    
    return True, None

def get_referral_stats(user_id):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_cards():
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('SELECT id, name, rate_per_hour, price_rub, description, emoji, min_referrals FROM cards ORDER BY id')
    cards = c.fetchall()
    conn.close()
    return cards

def get_card_by_id(card_id):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('SELECT id, name, rate_per_hour, price_rub, description, emoji, min_referrals FROM cards WHERE id = ?', (card_id,))
    card = c.fetchone()
    conn.close()
    return card

def create_purchase_request(user_id, card_id, amount_rub):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('INSERT INTO purchases (user_id, card_id, amount_rub, status) VALUES (?, ?, ?, "pending")',
              (user_id, card_id, amount_rub))
    conn.commit()
    purchase_id = c.lastrowid
    conn.close()
    return purchase_id

def confirm_purchase(purchase_id):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('SELECT user_id, card_id FROM purchases WHERE id = ? AND status = "pending"', (purchase_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, None
    
    user_id, card_id = row
    add_card_to_user(user_id, card_id, 1)
    c.execute('UPDATE purchases SET status = "completed" WHERE id = ?', (purchase_id,))
    conn.commit()
    conn.close()
    
    # Уведомление пользователю
    card = get_card_by_id(card_id)
    if card:
        send_msg(user_id, f"✅ ПОКУПКА ПОДТВЕРЖДЕНА!\n━━━━━━━━━━━━━━━\n{card[5]} {card[1]}\n📝 Статус: Добавлена в ферму\n━━━━━━━━━━━━━━━\n🎉 Поздравляем! Карта уже работает и приносит монеты!\n⚡ Скорость: +{card[2]} GPcoin/час", get_main_keyboard())
    
    return True, user_id

def calculate_earned(last_claim, rate):
    now = datetime.now()
    delta_hours = (now - last_claim).total_seconds() / 3600.0
    if delta_hours > 24:
        delta_hours = 24
    earned = int(delta_hours * rate)
    return earned, now

def get_top_players(limit=10):
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('''SELECT user_id, balance, total_earned FROM users ORDER BY balance DESC LIMIT ?''', (limit,))
    tops = c.fetchall()
    conn.close()
    
    result = []
    for uid, balance, total in tops:
        try:
            user_info = vk.users.get(user_ids=uid)[0]
            name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            name = f"ID{uid}"
        result.append((name, balance, total))
    
    return result

def create_withdrawal_request(user_id, amount, card_number, phone, bank, full_name):
    balance = get_user_balance(user_id)
    
    if amount < 1250:
        return False, "❌ Минимальная сумма вывода: 1250 GPcoin"
    
    if balance < amount:
        return False, f"❌ Недостаточно монет!\n💰 Ваш баланс: {balance} GPcoin\n💰 Запрошено: {amount} GPcoin"
    
    rub_amount = amount // EXCHANGE_RATE
    
    new_balance = balance - amount
    
    conn = sqlite3.connect('farm.db')
    c = conn.cursor()
    c.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    
    c.execute('SELECT total_withdrawn FROM users WHERE user_id = ?', (user_id,))
    current_withdrawn = c.fetchone()[0]
    c.execute('UPDATE users SET total_withdrawn = ? WHERE user_id = ?', (current_withdrawn + amount, user_id))
    
    c.execute('''INSERT INTO withdrawals (user_id, amount, rub_amount, card_number, phone, bank, full_name, status) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, "pending")''',
              (user_id, amount, rub_amount, card_number, phone, bank, full_name))
    
    withdrawal_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Уведомление пользователю
    send_msg(user_id, f"✅ ЗАЯВКА НА ВЫВОД СОЗДАНА!\n━━━━━━━━━━━━━━━\n💰 Сумма: {amount} GPcoin ({rub_amount} ₽)\n📝 Номер заявки: #{withdrawal_id}\n━━━━━━━━━━━━━━━\n⏳ Срок обработки: до 48 часов\n━━━━━━━━━━━━━━━\n💡 Статус заявки можно узнать у администратора.\n💰 Новый баланс: {new_balance} GPcoin", get_main_keyboard())
    
    try:
        user_info = vk.users.get(user_ids=user_id)[0]
        user_name = f"{user_info['first_name']} {user_info['last_name']}"
    except:
        user_name = f"ID{user_id}"
    
    admin_msg = f"🔔 НОВАЯ ЗАЯВКА НА ВЫВОД #{withdrawal_id}\n━━━━━━━━━━━━━━━\n👤 Игрок: {user_name}\n🆔 ID: {user_id}\n━━━━━━━━━━━━━━━\n💰 Сумма: {amount} GPcoin\n💵 В рублях: {rub_amount} ₽\n━━━━━━━━━━━━━━━\n💳 Номер: {card_number}\n🏦 Банк: {bank}\n👤 ФИО: {full_name}\n━━━━━━━━━━━━━━━\n✅ +вывод {withdrawal_id} - подтвердить\n❌ -вывод {withdrawal_id} - отменить"
    
    send_to_admin_chat(admin_msg)
    
    return True, f"✅ ЗАЯВКА НА ВЫВОД СОЗДАНА!\n━━━━━━━━━━━━━━━\n💰 Сумма: {amount} GPcoin ({rub_amount} ₽)\n📝 Номер заявки: #{withdrawal_id}\n━━━━━━━━━━━━━━━\n⏳ Срок обработки: до 48 часов\n━━━━━━━━━━━━━━━\n💡 Статус заявки можно узнать у администратора.\n💰 Новый баланс: {new_balance} GPcoin"

def generate_ref_link(user_id):
    return f"https://vk.com/club{GROUP_ID}?ref={user_id}"

def start_purchase_timeout(user_id, purchase_id):
    def timeout():
        import time
        time.sleep(20 * 60)
        if user_id in temp_purchases:
            data = temp_purchases[user_id]
            if data.get('purchase_id') == purchase_id and data.get('status') == 'waiting_payment':
                data['status'] = 'cancelled'
                send_msg(user_id, "⏰ ВРЕМЯ ОПЛАТЫ ИСТЕКЛО!\n━━━━━━━━━━━━━━━\nЗаявка на покупку автоматически отменена.\n🛒 Можете оформить новую заявку.", get_main_keyboard())
                
                try:
                    user_info = vk.users.get(user_ids=user_id)[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = f"ID{user_id}"
                
                send_to_admin_chat(f"⏰ ЗАЯВКА ОТМЕНЕНА (таймаут)\n━━━━━━━━━━━━━━━\n👤 {user_name}\n🆔 {user_id}\n📝 Заявка #{purchase_id}\nПричина: не оплачено в течение 20 минут")
    
    thread = threading.Thread(target=timeout)
    thread.daemon = True
    thread.start()

def check_and_notify_farm(user_id):
    """Проверяет накопление монет и отправляет уведомление"""
    data = get_user_data(user_id)
    if not data:
        return
    
    balance, last_claim, total_earned, total_withdrawn, referrer_id, created_at, total_rate = data
    earned, now = calculate_earned(last_claim, total_rate)
    
    # Уведомление каждые 4 часа, если накопилось больше порога
    last_notify = last_notify_time.get(user_id, datetime.min)
    hours_since_notify = (now - last_notify).total_seconds() / 3600
    
    if earned >= NOTIFY_FARM_THRESHOLD and hours_since_notify >= 4:
        last_notify_time[user_id] = now
        earned_rub = earned / EXCHANGE_RATE
        send_msg(user_id, f"⛏ НАПОМИНАНИЕ О ФАРМЕ\n━━━━━━━━━━━━━━━\nУ вас накопилось {earned} GPcoin ({earned_rub:.2f} ₽)!\n━━━━━━━━━━━━━━━\n⚡ Ваша ферма: {total_rate} GPcoin/час\n📝 Напишите '⛏ Фарм', чтобы забрать монеты!", get_main_keyboard())

def send_daily_discount(user_id):
    """Отправляет уведомление о случайной скидке (раз в день)"""
    cards = get_all_cards()
    available_cards = [c for c in cards if c[3] > 0]
    
    if not available_cards:
        return
    
    random_card = random.choice(available_cards)
    card_id, name, rate, price, desc, emoji, min_ref = random_card
    discount = random.randint(5, 25)
    new_price = int(price * (100 - discount) / 100)
    
    user_discounts[user_id] = {
        'card_id': card_id,
        'card_name': name,
        'emoji': emoji,
        'discount': discount,
        'new_price': new_price,
        'expires_at': datetime.now() + timedelta(hours=24)
    }
    
    send_msg(user_id, f"🎁 ПЕРСОНАЛЬНАЯ СКИДКА!\n━━━━━━━━━━━━━━━\n{emoji} {name}\n💰 Обычная цена: {price} ₽\n🔥 Ваша скидка: {discount}%\n💎 Цена сегодня: {new_price} ₽\n━━━━━━━━━━━━━━━\n⏰ Действует 24 часа!\n🛒 Напишите 'Купить {name} со скидкой'", get_main_keyboard())

# ---------- ОБРАБОТЧИК КОМАНД ----------
def handle_command(user_id, text):
    # Реферальная ссылка
    if 'ref=' in text:
        match = re.search(r'ref=(\d+)', text)
        if match:
            referrer_id = int(match.group(1))
            if referrer_id != user_id:
                temp_referrals[user_id] = referrer_id
                send_msg(user_id, "👋 Привет! Вы перешли по реферальной ссылке!\n\n🤝 Ваш друг пригласил вас в игру!\n✅ Напишите 'Старт', чтобы начать, и ваш друг получит бонус +10 монет!", get_welcome_keyboard())
                return
    
    # Проверка подписки
    if text not in ['Старт', 'start', '/start', '▶️ Начать игру', 'помощь', 'help', '❓ Помощь', '+админ', '/admin']:
        if not check_subscribe(user_id):
            send_msg(user_id, f"🔒 Игра доступна только подписчикам!\n\n👉 Подпишитесь: https://vk.com/club{GROUP_ID}", get_main_keyboard())
            return
    
    # СТАРТ
    if text in ['Старт', 'start', '/start', '▶️ Начать игру']:
        if not check_subscribe(user_id):
            send_msg(user_id, f"❌ Вы не подписаны!\n\n👉 Подпишитесь: https://vk.com/club{GROUP_ID}", get_main_keyboard())
            return
        
        referrer_id = temp_referrals.pop(user_id, None)
        success, ref_id = register_user(user_id, referrer_id)
        
        if not success:
            send_msg(user_id, "✅ Вы уже зарегистрированы в игре!\nИспользуйте кнопки для управления.", get_main_keyboard())
        else:
            if ref_id:
                send_msg(user_id, "🎮 ДОБРО ПОЖАЛОВАТЬ В ИГРУ!\n━━━━━━━━━━━━━━━\n🐢 Ваша первая видеокарта: GT 710\n⚡ Скорость: 1 GPcoin/час\n━━━━━━━━━━━━━━━\n🤝 Вы зарегистрировались по реферальной ссылке!\n💰 Ваш друг уже получил +10 GPcoin!\n━━━━━━━━━━━━━━━\n📱 Используйте кнопки для игры!", get_main_keyboard())
            else:
                ref_link = generate_ref_link(user_id)
                send_msg(user_id, f"🎮 ДОБРО ПОЖАЛОВАТЬ В ИГРУ!\n━━━━━━━━━━━━━━━\n🐢 Ваша первая видеокарта: GT 710\n⚡ Скорость: 1 GPcoin/час\n💰 Начальный баланс: 0 GPcoin\n━━━━━━━━━━━━━━━\n💱 КУРС ВЫВОДА: 10 GPcoin = 1 ₽\n━━━━━━━━━━━━━━━\n🤝 ПРИГЛАШАЙТЕ ДРУЗЕЙ!\n🔗 Ваша реферальная ссылка:\n{ref_link}\n💡 За каждого друга +10 GPcoin!\n💡 Пригласите 5 друзей и получите СЕКРЕТНУЮ КАРТУ!\n━━━━━━━━━━━━━━━\n🛒 КУПИТЬ ВИДЕОКАРТЫ ЗА РУБЛИ - кнопка 'Купить карты'\n📋 Все свои карты смотрите в 'Моя ферма'\n━━━━━━━━━━━━━━━\n📱 Используйте кнопки для игры!", get_main_keyboard())
        
        # Отправляем приветственную скидку
        send_daily_discount(user_id)
    
    # ФАРМ
    elif text in ['⛏ Фарм', '+фарм']:
        data = get_user_data(user_id)
        if not data:
            send_msg(user_id, "❌ Напишите 'Старт'", get_main_keyboard())
            return
        
        balance, last_claim, total_earned, total_withdrawn, referrer_id, created_at, total_rate = data
        
        if total_rate == 0:
            send_msg(user_id, "❌ У вас нет видеокарт! Купите их в магазине '🛒 Купить карты'", get_main_keyboard())
            return
        
        earned, now = calculate_earned(last_claim, total_rate)
        
        if earned == 0:
            send_msg(user_id, f"⏳ За это время ничего не нафармилось.\n\n⚡ Общая скорость: {total_rate} GPcoin/час\n💰 Баланс: {balance} GPcoin", get_main_keyboard())
            return
        
        new_balance = balance + earned
        new_total = total_earned + earned
        update_user_data(user_id, new_balance, now, new_total)
        
        earned_rub = earned / EXCHANGE_RATE
        
        send_msg(user_id, f"⛏ ВЫ ПОЛУЧИЛИ {earned} GPcoin ({earned_rub:.2f} ₽)!\n\n⚡ Общая скорость фермы: {total_rate} GPcoin/час\n━━━━━━━━━━━━━━━\n💰 Новый баланс: {new_balance} GPcoin\n💱 Курс вывода: 10 GPcoin = 1 ₽", get_main_keyboard())
        
        # Проверяем достижения
        if new_total >= 1000 and total_earned < 1000:
            send_msg(user_id, "🏆 ДОСТИЖЕНИЕ ПОЛУЧЕНО!\n━━━━━━━━━━━━━━━\n🎯 Первая 1000 GPcoin\n🎁 Награда: +100 GPcoin\n━━━━━━━━━━━━━━━\nПродолжайте в том же духе! 🚀", get_main_keyboard())
            update_user_data(user_id, new_balance + 100, now, new_total + 100)
        elif new_total >= 10000 and total_earned < 10000:
            send_msg(user_id, "🏆 ДОСТИЖЕНИЕ ПОЛУЧЕНО!\n━━━━━━━━━━━━━━━\n🎯 10000 GPcoin добыто!\n🎁 Награда: +500 GPcoin\n━━━━━━━━━━━━━━━\nВы настоящий майнер! 🔥", get_main_keyboard())
            update_user_data(user_id, new_balance + 500, now, new_total + 500)
    
    # МОЙ ПРОФИЛЬ
    elif text in ['📊 Мой профиль', '+профиль']:
        data = get_user_data(user_id)
        if not data:
            send_msg(user_id, "❌ Напишите 'Старт'", get_main_keyboard())
            return
        
        balance, last_claim, total_earned, total_withdrawn, referrer_id, created_at, total_rate = data
        referrals_count = get_referral_stats(user_id)
        
        days_in_game = (datetime.now() - created_at).days
        avg_per_day = total_earned // max(days_in_game, 1)
        
        user_cards = get_user_cards(user_id)
        total_cards = sum(card[4] for card in user_cards)
        
        send_msg(user_id, f"📊 МОЙ ПРОФИЛЬ\n━━━━━━━━━━━━━━━\n🖥 Всего карт: {total_cards}\n⚡ Общая скорость: {total_rate} GPcoin/час\n━━━━━━━━━━━━━━━\n💰 Баланс: {balance} GPcoin\n📈 Всего добыто: {total_earned} GPcoin\n💸 Всего выведено: {total_withdrawn} GPcoin\n━━━━━━━━━━━━━━━\n🔥 Дней в игре: {days_in_game}\n🤝 Приглашено друзей: {referrals_count}\n━━━━━━━━━━━━━━━\n💡 За час: +{total_rate} GPcoin\n💡 За день: +{total_rate * 24} GPcoin\n💡 Средний фарм в день: {avg_per_day} GPcoin\n━━━━━━━━━━━━━━━\n💱 Курс вывода: 10 GPcoin = 1 ₽", get_main_keyboard())
        
        # Проверяем уведомление о фарме
        check_and_notify_farm(user_id)
    
    # МОЯ ФЕРМА
    elif text in ['📋 Моя ферма', '+ферма']:
        user_cards = get_user_cards(user_id)
        
        if not user_cards:
            send_msg(user_id, "📋 У вас пока нет видеокарт!\n🛒 Купите их в магазине 'Купить карты'", get_main_keyboard())
            return
        
        total_rate = 0
        msg = "📋 МОЯ ФЕРМА\n━━━━━━━━━━━━━━━\n"
        
        for card_id, name, rate, emoji, quantity in user_cards:
            msg += f"{emoji} {name} x{quantity}\n   ⚡ {rate} GPcoin/час (всего: {rate * quantity})\n\n"
            total_rate += rate * quantity
        
        msg += f"━━━━━━━━━━━━━━━\n⚡ ОБЩАЯ СКОРОСТЬ: {total_rate} GPcoin/час\n"
        msg += f"💰 В день: {total_rate * 24} GPcoin ({total_rate * 24 / EXCHANGE_RATE:.2f} ₽)\n"
        msg += f"💎 В месяц: {total_rate * 720} GPcoin ({total_rate * 720 / EXCHANGE_RATE:.2f} ₽)\n"
        msg += "━━━━━━━━━━━━━━━\n💡 Покупайте ещё карты в '🛒 Купить карты'!"
        
        send_msg(user_id, msg, get_main_keyboard())
    
    # ВЫВОД
    elif text in ['💰 Вывод', '+вывод']:
        balance = get_user_balance(user_id)
        if balance is None:
            send_msg(user_id, "❌ Напишите 'Старт'", get_main_keyboard())
            return
        
        if balance < 1250:
            send_msg(user_id, f"❌ Недостаточно монет для вывода!\n💰 Ваш баланс: {balance} GPcoin\n💸 Минимальная сумма: 1250 GPcoin\n\n💰 Вам нужно накопить ещё {1250 - balance} GPcoin", get_main_keyboard())
            return
        
        user_withdraw_requests[user_id] = {'step': 'amount'}
        send_msg(user_id, f"💰 ВЫВОД СРЕДСТВ\n━━━━━━━━━━━━━━━\n💰 Ваш баланс: {balance} GPcoin\n💸 Минимальная сумма: 1250 GPcoin\n━━━━━━━━━━━━━━━\n📝 Введите сумму вывода (от 1250 до {balance} GPcoin):\n\nИли выберите из предложенных вариантов:", get_withdraw_amount_keyboard())
    
    # Обработка вывода
    elif text in ['1250', '2500', '5000', '10000', '25000', '50000', '100000'] and user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'amount':
        amount = int(text)
        balance = get_user_balance(user_id)
        
        if amount < 1250:
            send_msg(user_id, "❌ Сумма должна быть не менее 1250 GPcoin!", get_main_keyboard())
            return
        
        if amount > balance:
            send_msg(user_id, f"❌ Недостаточно монет! Ваш баланс: {balance} GPcoin", get_main_keyboard())
            return
        
        user_withdraw_requests[user_id] = {'step': 'card', 'amount': amount}
        send_msg(user_id, f"✅ Сумма: {amount} GPcoin ({amount//EXCHANGE_RATE} ₽)\n━━━━━━━━━━━━━━━\n📝 Введите номер карты или номер телефона для вывода:", get_withdraw_cancel_keyboard())
    
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'amount' and text.replace(' ', '').isdigit():
        amount = int(text.replace(' ', ''))
        balance = get_user_balance(user_id)
        
        if amount < 1250:
            send_msg(user_id, "❌ Сумма должна быть не менее 1250 GPcoin!", get_main_keyboard())
            return
        
        if amount > balance:
            send_msg(user_id, f"❌ Недостаточно монет! Ваш баланс: {balance} GPcoin", get_main_keyboard())
            return
        
        user_withdraw_requests[user_id] = {'step': 'card', 'amount': amount}
        send_msg(user_id, f"✅ Сумма: {amount} GPcoin ({amount//EXCHANGE_RATE} ₽)\n━━━━━━━━━━━━━━━\n📝 Введите номер карты или номер телефона для вывода:", get_withdraw_cancel_keyboard())
    
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'card':
        user_withdraw_requests[user_id]['card_number'] = text
        user_withdraw_requests[user_id]['step'] = 'bank'
        send_msg(user_id, "✅ Номер сохранён!\n━━━━━━━━━━━━━━━\n🏦 Введите название вашего банка (Тинькофф, Сбер, ВТБ и т.д.):", get_withdraw_cancel_keyboard())
    
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'bank':
        user_withdraw_requests[user_id]['bank'] = text
        user_withdraw_requests[user_id]['step'] = 'full_name'
        send_msg(user_id, "✅ Банк сохранён!\n━━━━━━━━━━━━━━━\n📝 Введите ваши ФИО полностью (как на карте):", get_withdraw_cancel_keyboard())
    
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'full_name':
        user_withdraw_requests[user_id]['full_name'] = text
        data = user_withdraw_requests[user_id]
        
        success, msg = create_withdrawal_request(
            user_id, 
            data['amount'], 
            data['card_number'], 
            data['card_number'],
            data['bank'], 
            data['full_name']
        )
        
        del user_withdraw_requests[user_id]
        send_msg(user_id, msg, get_main_keyboard())
    
    # ПОКУПКА КАРТ
    elif ' ₽' in text and ' | ' in text:
        card_name = text.split(' | ')[0].split(' ', 1)[1]
        
        cards = get_all_cards()
        for card in cards:
            card_id, name, rate, price_rub, desc, emoji, min_ref = card
            if name == card_name and price_rub > 0:
                purchase_id = create_purchase_request(user_id, card_id, price_rub)
                
                temp_purchases[user_id] = {
                    'purchase_id': purchase_id,
                    'card_id': card_id,
                    'card_name': name,
                    'price': price_rub,
                    'emoji': emoji,
                    'status': 'waiting_payment',
                    'expires_at': datetime.now() + timedelta(minutes=20)
                }
                
                start_purchase_timeout(user_id, purchase_id)
                
                send_msg(user_id, f"🛒 ПОКУПКА КАРТЫ\n━━━━━━━━━━━━━━━\n{emoji} {name}\n💰 Сумма: {price_rub} ₽\n━━━━━━━━━━━━━━━\n💳 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:\n\n🏦 Банк: Сбер\n💳 Номер карты: 2200 2061 9694 8710\n👤 Получатель: Владислав\n━━━━━━━━━━━━━━━\n📝 Номер заявки: #{purchase_id}\n⏳ Оплатите в течение 20 минут!\n━━━━━━━━━━━━━━━\n✅ После оплаты нажмите 'Я оплатил'", get_payment_keyboard())
                return
        
        send_msg(user_id, "❌ Карта не найдена", get_main_keyboard())
    
    # ПОКУПКА СО СКИДКОЙ
    elif 'со скидкой' in text and user_id in user_discounts:
        discount_data = user_discounts[user_id]
        if datetime.now() > discount_data['expires_at']:
            del user_discounts[user_id]
            send_msg(user_id, "⏰ Срок действия скидки истёк!\n🛒 Скидка больше не действует.", get_main_keyboard())
            return
        
        card_id = discount_data['card_id']
        card = get_card_by_id(card_id)
        if card:
            purchase_id = create_purchase_request(user_id, card_id, discount_data['new_price'])
            
            temp_purchases[user_id] = {
                'purchase_id': purchase_id,
                'card_id': card_id,
                'card_name': discount_data['card_name'],
                'price': discount_data['new_price'],
                'emoji': discount_data['emoji'],
                'status': 'waiting_payment',
                'expires_at': datetime.now() + timedelta(minutes=20)
            }
            
            start_purchase_timeout(user_id, purchase_id)
            
            send_msg(user_id, f"🛒 ПОКУПКА КАРТЫ СО СКИДКОЙ!\n━━━━━━━━━━━━━━━\n{discount_data['emoji']} {discount_data['card_name']}\n💰 Цена со скидкой: {discount_data['new_price']} ₽\n🔥 Вы сэкономили {discount_data['discount']}%!\n━━━━━━━━━━━━━━━\n💳 РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:\n\n🏦 Банк: Сбер\n💳 Номер карты: 2202 2061 9694 8710\n👤 Получатель: Владислав\n━━━━━━━━━━━━━━━\n📝 Номер заявки: #{purchase_id}\n⏳ Оплатите в течение 20 минут!\n━━━━━━━━━━━━━━━\n✅ После оплаты нажмите 'Я оплатил'", get_payment_keyboard())
            
            del user_discounts[user_id]
            return
        
        send_msg(user_id, "❌ Карта не найдена", get_main_keyboard())
    
    # КНОПКА "Я ОПЛАТИЛ"
    elif text == '✅ Я оплатил':
        if user_id not in temp_purchases:
            send_msg(user_id, "❌ У вас нет активных заявок на покупку.\n🛒 Выберите карту в магазине 'Купить карты'", get_main_keyboard())
            return
        
        data = temp_purchases[user_id]
        if data.get('status') != 'waiting_payment':
            send_msg(user_id, "❌ Ваша заявка уже обработана или отменена.", get_main_keyboard())
            return
        
        if datetime.now() > data['expires_at']:
            data['status'] = 'cancelled'
            del temp_purchases[user_id]
            send_msg(user_id, "⏰ ВРЕМЯ ОПЛАТЫ ИСТЕКЛО!\n━━━━━━━━━━━━━━━\nЗаявка автоматически отменена.\n🛒 Можете оформить новую заявку.", get_main_keyboard())
            return
        
        data['status'] = 'payment_confirmed'
        
        try:
            user_info = vk.users.get(user_ids=user_id)[0]
            user_name = f"{user_info['first_name']} {user_info['last_name']}"
        except:
            user_name = f"ID{user_id}"
        
        admin_msg = f"🔔 НОВАЯ ЗАЯВКА НА ПОКУПКУ #{data['purchase_id']}\n━━━━━━━━━━━━━━━\n👤 Игрок: {user_name}\n🆔 ID: {user_id}\n━━━━━━━━━━━━━━━\n{data['emoji']} {data['card_name']}\n💰 Сумма: {data['price']} ₽\n━━━━━━━━━━━━━━━\n✅ +покупка {data['purchase_id']} - подтвердить\n❌ -покупка {data['purchase_id']} - отменить"
        
        send_to_admin_chat(admin_msg)
        
        send_msg(user_id, f"✅ ЗАЯВКА НА ПОКУПКУ ОТПРАВЛЕНА!\n━━━━━━━━━━━━━━━\n📝 Номер заявки: #{data['purchase_id']}\n{data['emoji']} {data['card_name']}\n💰 Сумма: {data['price']} ₽\n━━━━━━━━━━━━━━━\n⏳ Статус: Ожидает проверки\n⏰ Срок проверки: до 24 часов\n━━━━━━━━━━━━━━━\n💡 Как только администратор подтвердит оплату,\nкарта автоматически появится в вашей ферме!", get_main_keyboard())
    
    # ОТМЕНА ПОКУПКИ
    elif text == '❌ Отмена' and user_id in temp_purchases:
        data = temp_purchases[user_id]
        data['status'] = 'cancelled'
        del temp_purchases[user_id]
        send_msg(user_id, "❌ Покупка отменена.", get_main_keyboard())
    
    # АДМИН-ПАНЕЛЬ
    elif text in ['+админ', '/admin'] and is_admin(user_id):
        send_msg(user_id, "🛠 АДМИН-ПАНЕЛЬ\n━━━━━━━━━━━━━━━\nВыберите действие:", get_admin_keyboard())
    
    elif text == '📋 Заявки на вывод' and is_admin(user_id):
        conn = sqlite3.connect('farm.db')
        c = conn.cursor()
        c.execute('SELECT id, user_id, amount, rub_amount, card_number, bank, full_name, created_at FROM withdrawals WHERE status = "pending" ORDER BY created_at ASC')
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            send_msg(user_id, "📋 Нет активных заявок на вывод.", get_main_keyboard())
            return
        
        msg = "📋 ЗАЯВКИ НА ВЫВОД\n━━━━━━━━━━━━━━━\n"
        for row in rows:
            withdrawal_id, uid, amount, rub, card, bank, name, created = row
            try:
                user_info = vk.users.get(user_ids=uid)[0]
                user_name = f"{user_info['first_name']} {user_info['last_name']}"
            except:
                user_name = f"ID{uid}"
            
            msg += f"#{withdrawal_id}\n👤 {user_name}\n💰 {amount} GPcoin ({rub} ₽)\n🏦 {bank}\n📅 {created[:10]}\n━━━━━━━━━━━━━━━\n"
        
        msg += "✅ +вывод [ID] - подтвердить\n❌ -вывод [ID] - отменить"
        send_msg(user_id, msg, get_main_keyboard())
    
    elif text == '🛒 Заявки на покупку' and is_admin(user_id):
        conn = sqlite3.connect('farm.db')
        c = conn.cursor()
        c.execute('SELECT id, user_id, card_id, amount_rub, created_at FROM purchases WHERE status = "pending" ORDER BY created_at ASC')
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            send_msg(user_id, "🛒 Нет активных заявок на покупку.", get_main_keyboard())
            return
        
        msg = "🛒 ЗАЯВКИ НА ПОКУПКУ\n━━━━━━━━━━━━━━━\n"
        for row in rows:
            purchase_id, uid, card_id, amount, created = row
            card = get_card_by_id(card_id)
            card_name = card[1] if card else "Неизвестно"
            try:
                user_info = vk.users.get(user_ids=uid)[0]
                user_name = f"{user_info['first_name']} {user_info['last_name']}"
            except:
                user_name = f"ID{uid}"
            
            msg += f"#{purchase_id}\n👤 {user_name}\n🖥 {card_name}\n💰 {amount} ₽\n📅 {created[:10]}\n━━━━━━━━━━━━━━━\n"
        
        msg += "✅ +покупка [ID] - подтвердить\n❌ -покупка [ID] - отменить"
        send_msg(user_id, msg, get_main_keyboard())
    
    elif text == '💰 Выдать монеты' and is_admin(user_id):
        user_withdraw_requests[user_id] = {'step': 'admin_give_coin_user'}
        send_msg(user_id, "💰 Введите ID пользователя и сумму через пробел\nПример: 123456789 1000", get_withdraw_cancel_keyboard())
    
    elif text == '🖥 Выдать карту' and is_admin(user_id):
        user_withdraw_requests[user_id] = {'step': 'admin_give_card_user'}
        send_msg(user_id, "🖥 Введите ID пользователя и ID карты через пробел\n\nID карт:\n1-GT710, 2-GT1030, 3-RX570, 4-GTX1660S, 5-RTX3060, 6-RTX4070, 7-RTX4090, 8-RX7900XTX, 9-Секретная\n\nПример: 123456789 7", get_withdraw_cancel_keyboard())
    
    elif text == '🎁 Скидка для игрока' and is_admin(user_id):
        user_withdraw_requests[user_id] = {'step': 'admin_give_discount'}
        send_msg(user_id, "🎁 Введите ID пользователя:\nПример: 123456789", get_withdraw_cancel_keyboard())
    
    elif text == '📊 Статистика бота' and is_admin(user_id):
        conn = sqlite3.connect('farm.db')
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        
        c.execute('SELECT SUM(balance) FROM users')
        total_balance = c.fetchone()[0] or 0
        
        c.execute('SELECT SUM(total_earned) FROM users')
        total_earned = c.fetchone()[0] or 0
        
        c.execute('SELECT SUM(total_withdrawn) FROM users')
        total_withdrawn = c.fetchone()[0] or 0
        
        c.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "pending"')
        pending_withdrawals = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM purchases WHERE status = "pending"')
        pending_purchases = c.fetchone()[0]
        
        c.execute('SELECT SUM(quantity) FROM user_cards')
        total_cards = c.fetchone()[0] or 0
        
        conn.close()
        
        send_msg(user_id, f"📊 СТАТИСТИКА БОТА\n━━━━━━━━━━━━━━━\n👥 Всего игроков: {total_users}\n🖥 Всего карт в игре: {total_cards}\n━━━━━━━━━━━━━━━\n💰 Монет в обороте: {total_balance}\n📈 Всего добыто: {total_earned}\n💸 Всего выведено: {total_withdrawn}\n━━━━━━━━━━━━━━━\n⏳ Заявок на вывод: {pending_withdrawals}\n🛒 Заявок на покупку: {pending_purchases}\n━━━━━━━━━━━━━━━\n💱 Курс вывода: 10 GPcoin = 1 ₽", get_main_keyboard())
    
    elif text == '📢 Рассылка' and is_admin(user_id):
        user_withdraw_requests[user_id] = {'step': 'admin_mailing'}
        send_msg(user_id, "📢 Введите текст рассылки для всех игроков:", get_withdraw_cancel_keyboard())
    
    # Админ-команды
    elif text.startswith('+вывод') and is_admin(user_id):
        parts = text.split()
        if len(parts) == 2:
            withdrawal_id = int(parts[1])
            
            conn = sqlite3.connect('farm.db')
            c = conn.cursor()
            c.execute('SELECT user_id, amount FROM withdrawals WHERE id = ? AND status = "pending"', (withdrawal_id,))
            row = c.fetchone()
            
            if row:
                user_id_buyer, amount = row
                c.execute('UPDATE withdrawals SET status = "completed" WHERE id = ?', (withdrawal_id,))
                conn.commit()
                conn.close()
                
                rub_amount = amount // EXCHANGE_RATE
                
                # Уведомление пользователю
                send_msg(user_id_buyer, f"✅ ВЫВОД ПОДТВЕРЖДЁН!\n━━━━━━━━━━━━━━━\n💰 Сумма: {rub_amount} ₽\n📝 Статус: Выполнен\n⏳ Деньги поступят в ближайшее время.\n━━━━━━━━━━━━━━━\nСпасибо, что играете с нами! 🎮", get_main_keyboard())
                send_msg(user_id, f"✅ Вывод #{withdrawal_id} подтверждён!")
                
                try:
                    user_info = vk.users.get(user_ids=user_id_buyer)[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = f"ID{user_id_buyer}"
                
                send_to_admin_chat(f"✅ ВЫВОД ПОДТВЕРЖДЁН\n━━━━━━━━━━━━━━━\n👤 {user_name}\n💰 {rub_amount} ₽\n📝 Заявка #{withdrawal_id}")
            else:
                send_msg(user_id, f"❌ Заявка #{withdrawal_id} не найдена или уже обработана")
        else:
            send_msg(user_id, "❌ Используйте: +вывод [номер_заявки]")
    
    elif text.startswith('-вывод') and is_admin(user_id):
        parts = text.split()
        if len(parts) == 2:
            withdrawal_id = int(parts[1])
            
            conn = sqlite3.connect('farm.db')
            c = conn.cursor()
            c.execute('SELECT user_id, amount FROM withdrawals WHERE id = ? AND status = "pending"', (withdrawal_id,))
            row = c.fetchone()
            
            if row:
                user_id_buyer, amount = row
                rub_amount = amount // EXCHANGE_RATE
                
                c.execute('SELECT balance FROM users WHERE user_id = ?', (user_id_buyer,))
                balance = c.fetchone()[0]
                c.execute('UPDATE users SET balance = ? WHERE user_id = ?', (balance + amount, user_id_buyer))
                
                c.execute('UPDATE withdrawals SET status = "cancelled" WHERE id = ?', (withdrawal_id,))
                conn.commit()
                conn.close()
                
                # Уведомление пользователю
                send_msg(user_id_buyer, f"❌ ВЫВОД ОТМЕНЁН\n━━━━━━━━━━━━━━━\n💰 Сумма: {rub_amount} ₽\n📝 Статус: Отменён\n💰 Средства возвращены на баланс.\n📞 По всем вопросам обратитесь к администратору.", get_main_keyboard())
                send_msg(user_id, f"❌ Вывод #{withdrawal_id} отменён, монеты возвращены")
                
                try:
                    user_info = vk.users.get(user_ids=user_id_buyer)[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = f"ID{user_id_buyer}"
                
                send_to_admin_chat(f"❌ ВЫВОД ОТМЕНЁН\n━━━━━━━━━━━━━━━\n👤 {user_name}\n💰 {rub_amount} ₽\n📝 Заявка #{withdrawal_id}")
            else:
                send_msg(user_id, f"❌ Заявка #{withdrawal_id} не найдена или уже обработана")
        else:
            send_msg(user_id, "❌ Используйте: -вывод [номер_заявки]")
    
    elif text.startswith('+покупка') and is_admin(user_id):
        parts = text.split()
        if len(parts) == 2:
            purchase_id = int(parts[1])
            success, user_id_buyer = confirm_purchase(purchase_id)
            
            if success:
                if user_id_buyer in temp_purchases:
                    del temp_purchases[user_id_buyer]
                send_msg(user_id, f"✅ Покупка #{purchase_id} подтверждена! Карта выдана.")
                
                try:
                    user_info = vk.users.get(user_ids=user_id_buyer)[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = f"ID{user_id_buyer}"
                
                send_to_admin_chat(f"✅ ПОКУПКА ПОДТВЕРЖДЕНА\n━━━━━━━━━━━━━━━\n👤 {user_name}\n📝 Заявка #{purchase_id}")
            else:
                send_msg(user_id, f"❌ {success}")
        else:
            send_msg(user_id, "❌ Используйте: +покупка [номер_заявки]")
    
    elif text.startswith('-покупка') and is_admin(user_id):
        parts = text.split()
        if len(parts) == 2:
            purchase_id = int(parts[1])
            
            conn = sqlite3.connect('farm.db')
            c = conn.cursor()
            c.execute('SELECT user_id FROM purchases WHERE id = ? AND status = "pending"', (purchase_id,))
            row = c.fetchone()
            
            if row:
                user_id_buyer = row[0]
                c.execute('UPDATE purchases SET status = "cancelled" WHERE id = ?', (purchase_id,))
                conn.commit()
                conn.close()
                
                # Уведомление пользователю
                send_msg(user_id_buyer, f"❌ ПОКУПКА ОТМЕНЕНА\n━━━━━━━━━━━━━━━\n📝 Ваша заявка на покупку отменена.\n📞 По всем вопросам обратитесь к администратору.", get_main_keyboard())
                send_msg(user_id, f"❌ Покупка #{purchase_id} отменена")
                
                try:
                    user_info = vk.users.get(user_ids=user_id_buyer)[0]
                    user_name = f"{user_info['first_name']} {user_info['last_name']}"
                except:
                    user_name = f"ID{user_id_buyer}"
                
                send_to_admin_chat(f"❌ ПОКУПКА ОТМЕНЕНА\n━━━━━━━━━━━━━━━\n👤 {user_name}\n📝 Заявка #{purchase_id}")
            else:
                send_msg(user_id, f"❌ Заявка #{purchase_id} не найдена или уже обработана")
        else:
            send_msg(user_id, "❌ Используйте: -покупка [номер_заявки]")
    
    # Обработка админ-ввода
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'admin_give_coin_user':
        parts = text.split()
        if len(parts) == 2:
            try:
                target_user = int(parts[0])
                amount = int(parts[1])
                
                conn = sqlite3.connect('farm.db')
                c = conn.cursor()
                c.execute('SELECT balance FROM users WHERE user_id = ?', (target_user,))
                row = c.fetchone()
                
                if row:
                    new_balance = row[0] + amount
                    c.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, target_user))
                    conn.commit()
                    conn.close()
                    
                    try:
                        user_info = vk.users.get(user_ids=target_user)[0]
                        user_name = f"{user_info['first_name']} {user_info['last_name']}"
                    except:
                        user_name = f"ID{target_user}"
                    
                    send_msg(user_id, f"✅ Выдано {amount} GPcoin пользователю {user_name}")
                    send_msg(target_user, f"💰 Администратор выдал вам {amount} GPcoin!\n💰 Новый баланс: {new_balance} GPcoin", get_main_keyboard())
                    
                    send_to_admin_chat(f"💰 ВЫДАЧА МОНЕТ\n━━━━━━━━━━━━━━━\n👤 {user_name}\n💰 {amount} GPcoin")
                else:
                    send_msg(user_id, "❌ Пользователь не найден")
            except:
                send_msg(user_id, "❌ Неверный формат. Используйте: ID сумма")
        else:
            send_msg(user_id, "❌ Неверный формат. Используйте: ID сумма")
        
        del user_withdraw_requests[user_id]
    
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'admin_give_card_user':
        parts = text.split()
        if len(parts) == 2:
            try:
                target_user = int(parts[0])
                card_id = int(parts[1])
                
                card = get_card_by_id(card_id)
                if not card:
                    send_msg(user_id, "❌ Карта не найдена")
                else:
                    add_card_to_user(target_user, card_id, 1)
                    
                    try:
                        user_info = vk.users.get(user_ids=target_user)[0]
                        user_name = f"{user_info['first_name']} {user_info['last_name']}"
                    except:
                        user_name = f"ID{target_user}"
                    
                    send_msg(user_id, f"✅ Выдана карта {card[1]} пользователю {user_name}")
                    send_msg(target_user, f"🖥 Администратор выдал вам карту {card[5]} {card[1]}!\n📋 Она добавлена в вашу ферму!", get_main_keyboard())
                    
                    send_to_admin_chat(f"🖥 ВЫДАЧА КАРТЫ\n━━━━━━━━━━━━━━━\n👤 {user_name}\n🖥 {card[1]}")
            except:
                send_msg(user_id, "❌ Неверный формат. Используйте: ID ID_карты")
        else:
            send_msg(user_id, "❌ Неверный формат. Используйте: ID ID_карты")
        
        del user_withdraw_requests[user_id]
    
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'admin_give_discount':
        try:
            target_user = int(text)
            send_daily_discount(target_user)
            send_msg(user_id, f"✅ Скидка отправлена пользователю!")
            
            try:
                user_info = vk.users.get(user_ids=target_user)[0]
                user_name = f"{user_info['first_name']} {user_info['last_name']}"
            except:
                user_name = f"ID{target_user}"
            
            send_to_admin_chat(f"🎁 СКИДКА ВЫДАНА\n━━━━━━━━━━━━━━━\n👤 {user_name}")
        except:
            send_msg(user_id, "❌ Неверный ID пользователя")
        
        del user_withdraw_requests[user_id]
    
    elif user_id in user_withdraw_requests and user_withdraw_requests[user_id].get('step') == 'admin_mailing':
        message = text
        
        conn = sqlite3.connect('farm.db')
        c = conn.cursor()
        c.execute('SELECT user_id FROM users')
        users = c.fetchall()
        conn.close()
        
        success_count = 0
        for user in users:
            try:
                send_msg(user[0], f"📢 РАССЫЛКА ОТ АДМИНИСТРАЦИИ\n━━━━━━━━━━━━━━━\n{message}\n━━━━━━━━━━━━━━━\nСпасибо, что играете с нами! 🎮", get_main_keyboard())
                success_count += 1
            except:
                pass
        
        send_msg(user_id, f"✅ Рассылка отправлена {success_count} игрокам!")
        
        send_to_admin_chat(f"📢 РАССЫЛКА\n━━━━━━━━━━━━━━━\nОтправлено {success_count} игрокам\n📝 Текст: {message[:100]}...")
        
        del user_withdraw_requests[user_id]
    
    elif text == '◀️ Назад':
        if user_id in user_withdraw_requests:
            del user_withdraw_requests[user_id]
        if user_id in temp_purchases:
            del temp_purchases[user_id]
        send_msg(user_id, "🔙 Главное меню", get_main_keyboard())
    
    # КУПИТЬ КАРТЫ
    elif text in ['🛒 Купить карты', '+купить']:
        cards = get_all_cards()
        msg = "🛒 МАГАЗИН ВИДЕОКАРТ\n━━━━━━━━━━━━━━━\n"
        for card in cards:
            card_id, name, rate, price_rub, desc, emoji, min_ref = card
            if price_rub > 0:
                msg += f"{emoji} {name}\n   ⚡ {rate} GPcoin/час\n   💰 Цена: {price_rub} ₽\n   📝 {desc}\n\n"
            else:
                msg += f"{emoji} {name}\n   ⚡ {rate} GPcoin/час\n   💰 Цена: Бесплатно (за 5 друзей)\n   📝 {desc}\n   🤝 Требуется друзей: {min_ref}\n\n"
        msg += "━━━━━━━━━━━━━━━\n💡 Нажмите на кнопку с картой, чтобы купить!\n💳 Оплата производится через администратора.\n📝 После оплаты нажмите 'Я оплатил'"
        
        send_msg(user_id, msg, get_cards_shop_keyboard())
    
    # ТОП ИГРОКОВ
    elif text in ['👑 Топ игроков', '+топ']:
        tops = get_top_players(10)
        if not tops:
            send_msg(user_id, "📊 Пока нет игроков в топе.", get_main_keyboard())
            return
        
        msg = "👑 ТОП ИГРОКОВ ПО БАЛАНСУ\n━━━━━━━━━━━━━━━\n"
        for i, (name, balance, total) in enumerate(tops, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            msg += f"{medal} {name}\n   💰 {balance} GPcoin\n\n"
        
        send_msg(user_id, msg, get_main_keyboard())
    
    # РЕФЕРАЛЫ
    elif text in ['🤝 Рефералы', '+рефералы']:
        referrals_count = get_referral_stats(user_id)
        ref_link = generate_ref_link(user_id)
        
        send_msg(user_id, f"🤝 РЕФЕРАЛЬНАЯ СИСТЕМА\n━━━━━━━━━━━━━━━\n👥 Приглашено друзей: {referrals_count}\n💰 За каждого друга: +10 GPcoin (1 ₽)\n━━━━━━━━━━━━━━━\n🔗 ВАША РЕФЕРАЛЬНАЯ ССЫЛКА:\n{ref_link}\n━━━━━━━━━━━━━━━\n💡 КАК ЭТО РАБОТАЕТ:\n1️⃣ Отправьте ссылку другу\n2️⃣ Друг переходит по ссылке\n3️⃣ Друг пишет 'Старт'\n4️⃣ Вы получаете +10 GPcoin!\n━━━━━━━━━━━━━━━\n🎁 БОНУС: Пригласите 5 друзей и получите СЕКРЕТНУЮ КАРТУ!\n━━━━━━━━━━━━━━━\n🎯 Осталось пригласить: {max(0, 5 - referrals_count)} друзей", get_main_keyboard())
    
    # ПОМОЩЬ
    elif text in ['❓ Помощь', 'помощь', 'help']:
        send_msg(user_id, "🎮 ИГРА-ФАРМИЛКА ВИДЕОКАРТ\n━━━━━━━━━━━━━━━\n📱 КНОПКИ УПРАВЛЕНИЯ:\n• ⛏ Фарм - собрать монеты\n• 📊 Мой профиль - статистика\n• 💰 Вывод - вывести монеты\n• 🛒 Купить карты - магазин за рубли\n• 📋 Моя ферма - все ваши карты\n• 👑 Топ игроков - рейтинг\n• 🤝 Рефералы - приглашай друзей\n━━━━━━━━━━━━━━━\n💡 КАК КУПИТЬ КАРТУ:\n1️⃣ Нажмите '🛒 Купить карты'\n2️⃣ Выберите карту\n3️⃣ Переведите деньги по реквизитам\n4️⃣ Нажмите '✅ Я оплатил'\n5️⃣ Администратор подтвердит покупку\n6️⃣ Карта появится в вашей ферме!\n━━━━━━━━━━━━━━━\n💡 КАК ВЫВЕСТИ ДЕНЬГИ:\n1️⃣ Нажмите '💰 Вывод'\n2️⃣ Введите сумму (от 1250 GPcoin)\n3️⃣ Укажите реквизиты\n4️⃣ Заявка уйдёт администратору\n5️⃣ Ожидайте выплаты (до 48 часов)\n━━━━━━━━━━━━━━━\n🎁 БОНУСЫ:\n• За каждого друга +10 GPcoin\n• За 5 друзей - СЕКРЕТНАЯ КАРТА\n• Достижения за 1000 и 10000 GPcoin\n• Персональные скидки каждый день!\n━━━━━━━━━━━━━━━\n💰 ВЫВОД: от 1250 GPcoin (125 ₽)\n━━━━━━━━━━━━━━━\n💱 КУРС ВЫВОДА: 10 GPcoin = 1 ₽\n━━━━━━━━━━━━━━━\n🎯 Цель: создать самую мощную ферму и зарабатывать пассивный доход!", get_main_keyboard())
    
    else:
        if text and text[0] != '+':
            send_msg(user_id, "❓ Неизвестная команда\nНапишите 'Старт' или 'Помощь'", get_main_keyboard())

# ---------- ГЛАВНЫЙ ЦИКЛ ----------
print("🤖 БОТ ЗАПУЩЕН")
print(f"📱 Группа ID: {GROUP_ID}")
print(f"💬 Админ-чат ID: {ADMIN_CHAT_ID}")
print(f"👑 Администраторы: {ADMIN_IDS}")
print(f"💱 Курс вывода: {EXCHANGE_RATE} GPcoin = 1 ₽")
print(f"🔔 Уведомления о фарме: при накоплении {NOTIFY_FARM_THRESHOLD}+ монет")
print("━━━━━━━━━━━━━━━━━━━━━━━")
print("Ожидание сообщений...")

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_id = event.user_id
        text = event.text.strip()
        
        try:
            handle_command(user_id, text)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            send_msg(user_id, "⚠ Произошла ошибка. Попробуйте позже.", get_main_keyboard())