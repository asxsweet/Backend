# 📦 Flask + Firebase API

Бұл жоба Flask арқылы жасалған backend жүйе. Қолданушылар тіркеліп, жүйеге кіріп, суреттер жүктеп, посттармен әрекеттесе алады. Деректер Firebase Firestore, Authentication және Storage арқылы өңделеді.

---

## 🔐 Авторизация

### 🟩 Тіркелу
**POST** `/signup`  
**Body:**
```json
{
  "email": "user@example.com",
  "password": "12345678",
  "name": "User Name"
}
```

---

### 🟩 Кіру
**POST** `/login`  
**Body:**
```json
{
  "email": "user@example.com",
  "password": "12345678"
}
```

**Response:**
```json
{
  "msg": "Кіру сәтті өтті",
  "idToken": "JWT токен",
  "uid": "қолданушы UID"
}
```

---

## 📸 Посттар

### 🟨 Пост жүктеу
**POST** `/upload_post`  
**Headers:** `Authorization: Bearer <idToken>`  
**Form-data:**
- `image`: файл
- `caption`: сипаттама

---

### 🟨 Барлық посттарды көру
**GET** `/feed`  
**GET** `/feed?sort=likes` ← лайк санына қарай сұрыптау

---

### 🟨 Өз посттарын көру
**GET** `/my_posts`  
**Headers:** `Authorization: Bearer <idToken>`

---

### 🟨 Постты өңдеу
**POST** `/edit_post/<post_id>`  
**Headers:** `Authorization`  
**Body:**
```json
{
  "caption": "Жаңартылған сипаттама"
}
```

---

### 🟨 Постты өшіру
**DELETE** `/delete_post/<post_id>`  
**Headers:** `Authorization`

---

## ❤️ Лайк

### 🔸 Лайк басу
**POST** `/like_post/<post_id>`  
**Headers:** `Authorization`

---

## 💬 Пікірлер

### 🔸 Пікір қалдыру
**POST** `/comment/<post_id>`  
**Headers:** `Authorization`  
**Body:**
```json
{
  "text": "Керемет пост екен!"
}
```

---

### 🔸 Пікірлерді көру
**GET** `/comments/<post_id>`

---

## 👤 Қолданушы профилі

### 🔹 Профильді көру
**GET** `/profile/<uid>`

---

### 🔹 Профильді өңдеу
**POST** `/edit_profile`  
**Headers:** `Authorization`  
**Body:**
```json
{
  "name": "Жаңа Аты",
  "photo_url": "https://example.com/avatar.jpg"
}
```

---

## 🔎 Іздеу

**GET** `/search?keyword=күн`

---

## 📊 Соңғы кіру уақыты

Қолданушы жүйеге кірген кезде Firestore → `users` коллекциясында `last_login` өрісі жаңарады.

---

## 🛠 Қате өңдеу

Қате болғанда JSON жауап қайтарылады:

```json
{
  "error": "Қате сипаттамасы"
}
```

---

## ✅ Нәтиже

Бұл API келесі мүмкіндіктерді қамтиды:

- 🔐 Тіркелу / Кіру / Авторизация
- 📸 Пост жүктеу, өңдеу, өшіру
- ❤️ Лайк жүйесі
- 💬 Пікір қалдыру және көру
- 🔎 Іздеу / сұрыптау
- 👤 Профиль өңдеу
- 📊 Соңғы кіру уақыты# B a c k e n d  
 