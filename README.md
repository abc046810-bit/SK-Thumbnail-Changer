# SK Thumbnail Changer

Premium Telegram bot that replaces the video thumbnail with a stylish **Telegram logo + @username** text.

**Default name:** `@The_Sk08`  
**Owner:** `@SunilChoudhary08`

## Features
- Works with **any size video** (20 MB → 2 GB) using `file_id` + existing thumbnail method
- Stylish black bar + Telegram logo + outlined white text
- Full authorization system (only owner + authorized users)
- Beautiful inline button UI + all commands
- Free Render Web Service ready
- Persistent authorized list (`authorized.json`)

## Commands

### For Authorized Users
| Command | Description |
|---------|-------------|
| `/start` | Start bot + show main menu with buttons |
| `/help` | Show all commands + usage guide |
| `/setname <name>` | Set your custom stylish name (e.g. `/setname The_Sk08`) |
| `/myname` | See currently set name |
| `/cancel` | Cancel current action |

### Owner Only (`@SunilChoudhary08`)
| Command | Description |
|---------|-------------|
| `/authorize <user_id>` | Allow a user to use the bot |
| `/unauthorize <user_id>` | Remove access |
| `/listauth` | List all authorized user IDs |

## How to Use (User)
1. Owner se access lo (agar nahi hai)
2. `/start` → buttons dikhenge
3. `/setname ApnaNaam` (warna default `@The_Sk08` lagega)
4. Koi bhi video bhejo
5. Bot 1-2 second me naya thumbnail laga ke wapas bhej dega

## Buttons (Premium UI)
- **Set Name** → naam set karne ka tarika
- **My Name** → current naam dekho
- **How to Use** → simple steps
- **Help & Commands** → full list
- **Owner Panel** (sirf owner ko dikhta hai) → authorize / remove / list

## Deploy on Free Render (Web Service)

1. Is folder ko zip karke Render pe **Web Service** banao
2. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Environment Variables:
   ```
   BOT_TOKEN = <BotFather se mila token>
   WEBHOOK_URL = https://your-service-name.onrender.com
   ```
4. Deploy → Deploy hone ke baad ek baar **Manual Deploy** / Restart kar dena (webhook set hone ke liye)

## Project Structure
```
telegram_thumb_bot/
├── main.py
├── requirements.txt
├── .env.example
├── authorized.json          ← auto-created
├── assets/
│   ├── telegram_logo.png
│   └── AlegreyaSans-Bold.ttf
└── README.md
```

## Notes
- Unauthorized users ko clear "Access Denied" message milta hai
- Owner hamesha authorized rehta hai
- Badi video me Telegram ka ready thumbnail use hota hai → isliye 2GB bhi chal jata hai
- Free Render pe perfect kaam karta hai

Made with ❤️ for SK
