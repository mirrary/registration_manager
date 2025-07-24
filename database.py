import json
import os
import itertools
from typing import Dict, List, Optional, Tuple, Set, Union

from config import GMAILS_FILE, DATABASE_FILE


class Database:
    def __init__(self):
        """Инициализация базы данных."""
        self.gmails = self._load_gmails()
        self.services_data = self._load_services_data()
        self._migrate_data_if_needed()

    def _load_gmails(self) -> List[str]:
        """Загрузка списка почт из файла."""
        try:
            with open(GMAILS_FILE, 'r') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"Файл {GMAILS_FILE} не найден.")
            return []

    def _load_services_data(self) -> Dict[str, Union[str, List[str]]]:
        """Загрузка данных о привязках сервисов к почтам."""
        if os.path.exists(DATABASE_FILE):
            try:
                with open(DATABASE_FILE, 'r') as file:
                    return json.load(file)
            except json.JSONDecodeError:
                print(f"Ошибка при чтении файла {DATABASE_FILE}. Создаем новый.")
                return {}
        return {}

    def _migrate_data_if_needed(self) -> None:
        """Миграция данных со старого формата на новый, если необходимо."""
        need_save = False
        for service, value in list(self.services_data.items()):
            if isinstance(value, str):
                # Конвертируем строку в список
                self.services_data[service] = [value]
                need_save = True
        
        if need_save:
            self._save_services_data()

    def _save_services_data(self) -> None:
        """Сохранение данных о привязках сервисов к почтам."""
        with open(DATABASE_FILE, 'w') as file:
            json.dump(self.services_data, file, indent=4)

    def get_all_used_gmails(self) -> Set[str]:
        """Получение всех используемых почт."""
        used_gmails = set()
        for emails in self.services_data.values():
            if isinstance(emails, list):
                used_gmails.update(emails)
            else:
                # На случай, если остались старые данные
                used_gmails.add(emails)
        return used_gmails

    def get_unused_gmail(self) -> Optional[str]:
        """Получение неиспользованной почты."""
        used_gmails = self.get_all_used_gmails()
        for gmail in self.gmails:
            if gmail not in used_gmails:
                return gmail
        return None

    def get_unused_gmail_for_service(self, service_name: str) -> Optional[str]:
        """
        Получение неиспользованной почты для конкретного сервиса.
        Возвращает почту, которая еще не использовалась для этого сервиса.
        """
        service_name = service_name.lower()
        service_emails = self.services_data.get(service_name, [])
        
        # Преобразуем в список, если это строка (для обратной совместимости)
        if isinstance(service_emails, str):
            service_emails = [service_emails]
        
        # Получаем множество всех почт, используемых для этого сервиса
        used_for_service = set(service_emails)
        
        # Ищем почту, которая еще не использовалась для этого сервиса
        for gmail in self.gmails:
            if gmail not in used_for_service:
                return gmail
        
        return None

    def get_service_gmails(self, service_name: str) -> List[str]:
        """Получение списка почт, привязанных к сервису."""
        service_name = service_name.lower()
        emails = self.services_data.get(service_name, [])
        
        # Преобразуем в список, если это строка (для обратной совместимости)
        if isinstance(emails, str):
            return [emails]
        return emails

    def get_latest_service_gmail(self, service_name: str) -> Optional[str]:
        """Получение последней почты, привязанной к сервису."""
        emails = self.get_service_gmails(service_name)
        if emails:
            return emails[-1]
        return None

    def assign_gmail_to_service(self, service_name: str, gmail: str) -> None:
        """Привязка почты к сервису."""
        service_name = service_name.lower()
        
        if service_name not in self.services_data:
            self.services_data[service_name] = []
        
        # Преобразуем в список, если это строка (для обратной совместимости)
        if isinstance(self.services_data[service_name], str):
            self.services_data[service_name] = [self.services_data[service_name]]
        
        # Добавляем почту в список, если её там еще нет
        if gmail not in self.services_data[service_name]:
            self.services_data[service_name].append(gmail)
            self._save_services_data()

    def check_and_assign_gmail(self, service_name: str) -> Tuple[bool, str]:
        """
        Проверка наличия привязки и привязка новой почты при необходимости.
        
        Returns:
            Tuple[bool, str]: (существовала ли привязка, почта)
        """
        service_name = service_name.lower()
        existing_gmail = self.get_latest_service_gmail(service_name)
        
        if existing_gmail:
            return True, existing_gmail
        
        new_gmail = self.get_unused_gmail_for_service(service_name)
        if new_gmail:
            self.assign_gmail_to_service(service_name, new_gmail)
            return False, new_gmail
        
        return False, "Нет доступных почт"
        
    def generate_domain_names(self, email: str) -> int:
        """
        Генерирует все возможные комбинации доменных имен для Gmail и сохраняет их в файл.
        Очищает все предыдущие данные о привязках сервисов.
        
        Args:
            email: Базовая почта для генерации (например, example@gmail.com)
            
        Returns:
            int: Количество сгенерированных почт
        """
        # Проверяем, что это Gmail
        if not email.endswith('@gmail.com'):
            raise ValueError("Почта должна быть Gmail (@gmail.com)")
        
        # Получаем имя пользователя (часть до @)
        username = email.split('@')[0]
        
        # Генерируем все возможные комбинации с точками
        generated_emails = []
        
        # Добавляем оригинальную почту
        generated_emails.append(email)
        
        # Генерируем все возможные комбинации с точками
        for i in range(1, len(username)):
            # Получаем все возможные позиции для вставки точек
            positions = list(itertools.combinations(range(1, len(username)), i))
            
            for pos in positions:
                # Создаем новое имя пользователя с точками в указанных позициях
                new_username = username
                # Вставляем точки с конца, чтобы не сдвигать индексы
                for p in sorted(pos, reverse=True):
                    new_username = new_username[:p] + '.' + new_username[p:]
                
                # Добавляем новую почту в список
                new_email = f"{new_username}@gmail.com"
                generated_emails.append(new_email)
        
        # Сохраняем сгенерированные почты в файл
        with open(GMAILS_FILE, 'w') as file:
            for email in generated_emails:
                file.write(f"{email}\n")
        
        # Обновляем список почт в памяти
        self.gmails = generated_emails
        
        # Очищаем данные о привязках сервисов
        self.services_data = {}
        self._save_services_data()
        
        return len(generated_emails)
