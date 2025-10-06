import asyncio
import asyncpg

async def check():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='FamilyDB',
        user='postgres',
        password='1'
    )
    
    rows = await conn.fetch('SELECT id, file_id, caption, ticket_url FROM posters ORDER BY id DESC LIMIT 1')
    
    if rows:
        for row in rows:
            print(f"\n=== Последняя афиша ===")
            print(f"ID: {row['id']}")
            print(f"File ID: {row['file_id']}")
            print(f"Caption: {row['caption'][:50] if row['caption'] else 'None'}...")
            print(f"Ticket URL: {row['ticket_url']}")
    else:
        print("Нет афиш в БД")
    
    await conn.close()

asyncio.run(check())
