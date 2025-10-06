import asyncio
from db_config import Database, UserRepository, PosterRepository, AttendanceRepository

async def test_database_operations():
    # Инициализация подключения к базе данных
    await Database.get_pool()
    
    try:
        # Тестируем работу с пользователями
        print("🧪 Тестирование работы с пользователями...")
        test_user = {
            'tg_id': 123456789,
            'name': 'Тестовый Пользователь',
            'gender': 'male',
            'age': 25,
            'vk_id': 'id12345678'
        }
        
        # Создаем/обновляем пользователя
        user = await UserRepository.create_or_update_user(test_user)
        print(f"✅ Пользователь создан/обновлен: {user['name']} (ID: {user['tg_id']})")
        
        # Получаем пользователя по ID
        user = await UserRepository.get_user(test_user['tg_id'])
        print(f"ℹ️ Получен пользователь: {user['name']} (Возраст: {user['age']}, Пол: {user['gender']})")
        
        # Тестируем работу с афишами
        print("\n🎭 Тестирование работы с афишами...")
        test_poster = {
            'file_id': 'test_file_id_123',
            'caption': 'Тестовое мероприятие',
            'ticket_url': 'https://example.com/tickets/123',
            'is_active': True
        }
        
        # Создаем афишу
        poster = await PosterRepository.create_poster(test_poster)
        print(f"✅ Афиша создана: {poster['caption']} (ID: {poster['id']})")
        
        # Получаем список активных афиш
        posters = await PosterRepository.get_active_posters()
        print(f"ℹ️ Всего активных афиш: {len(posters)}")
        
        # Тестируем отметку о посещении
        print("\n📝 Тестирование отметок о посещении...")
        attendance = await AttendanceRepository.mark_attendance(
            user_id=test_user['tg_id'],
            poster_id=poster['id']
        )
        print(f"✅ Пользователь отмечен на мероприятии: {attendance['attended_at']}")
        
        # Получаем список посещений пользователя
        attendances = await AttendanceRepository.get_user_attendances(test_user['tg_id'])
        print(f"ℹ️ Всего посещений пользователя: {len(attendances)}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        # Закрываем соединение с базой данных
        await Database.close_pool()
        print("\n🔌 Соединение с базой данных закрыто")

if __name__ == "__main__":
    print("🚀 Запуск теста работы с базой данных...\n")
    asyncio.run(test_database_operations())
