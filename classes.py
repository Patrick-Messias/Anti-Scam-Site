from __future__ import annotations
from typing import TYPE_CHECKING
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import re # Para validação de URL do YouTube

if TYPE_CHECKING: from database import Database # type: ignore

class ClassUtils:
    def __init__(self):
        self.value = None
        
    def atr_get(self, attr_name: list):
        return [getattr(self, atn) for atn in attr_name]
    
    def atr_modify(self, attr_name: list, value_new: list): 
        for atn, new_atn in zip(attr_name, value_new): 
            setattr(self, atn, new_atn)
        
    def atr_delete(self, attr_name: list): 
        for atn in attr_name:
            if hasattr(self, atn): 
                delattr(self, atn)
        
    def atr_list(self):
        print(vars(self))

    @staticmethod
    def is_valid_email(email):
        """Valida um endereço de e-mail usando uma expressão regular."""
        # Expressão regular para validar e-mails
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(email_regex) is not None

class Site(ClassUtils):
    def __init__(self, name: str, url: str):
        super().__init__()
        self.name = name
        self.url = url

    @classmethod
    def validate_url(cls, url: str) -> bool:
        return url.startswith(('http://', 'https://'))


class User(ClassUtils, UserMixin):
    # Parâmetros na ordem correta para correspondência com os dados do DB
    def __init__(self, id, name, email, password_hash, type_user='noob', confidence=1.0, 
                 age=None, city=None, state=None, civil_state=None):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash
        self.type_user = type_user  # Ex: 'admin', 'moderator', 'noob', 'expert'
        self.confidence = float(confidence) # Garante que confidence é um float, corrigindo o ValueError
        self.age = age
        self.city = city
        self.state = state
        self.civil_state = civil_state

    def get_id(self):
        """Retorna o ID do usuário como string, como esperado pelo Flask-Login."""
        return str(self.id)

    def permissions_set(self):
        self.can_check_tutorials = self.confidence >= 1.0
        self.can_register_scam = self.confidence >= 1.0
        self.can_approve_scam = self.confidence >= 2.0
        self.can_manage_tutorials = self.confidence >= 3.0 # Nova permissão para gerenciar tutoriais

    def report_scam(self, name: str, site: Site, type_scam: str, evidence: str) -> DigitalScam:
        if not self.can_register_scam:
            raise PermissionError("User lacks permissions to report scams.")
        return DigitalScam(name, site, type_scam, 0.0, 0.0, evidence, self)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)
    
class UserNoob(User):
    def __init__(self, id, name, email, password_hash, age=None, city=None, state=None, civil_state=None):
        super().__init__(id=id, name=name, email=email, password_hash=password_hash,
                        type_user='noob', confidence=1.0, age=age, city=city, state=state, civil_state=civil_state)

class UserExpert(User):
    def __init__(self, id, name, email, password_hash, age=None, city=None, state=None, civil_state=None):
        super().__init__(id=id, name=name, email=email, password_hash=password_hash,
                        type_user='expert', confidence=2.0, age=age, city=city, state=state, civil_state=civil_state)

class Admin(User):
    def __init__(self, id, name, email, password_hash, age=None, city=None, state=None, civil_state=None):
        super().__init__(id=id, name=name, email=email, password_hash=password_hash,
                        type_user='admin', confidence=3.0, age=age, city=city, state=state, civil_state=civil_state)

class DigitalScam(ClassUtils):
    def __init__(self, name: str, site: Site, type_scam: str, impact_score: float, risk_level: float, evidence: str, reporter: User):
        super().__init__()
        self.name = name
        self.site = site
        self.type_scam = type_scam
        self.impact_score = impact_score
        self.risk_level = risk_level
        self.evidence = evidence
        self.reporter = reporter

class Tutorial(ClassUtils):
    def __init__(self, id: int, title: str, content: str, youtube_link: str, user_id: int, created_at: str, author: str):
        super().__init__()
        self.id = id
        self.title = title
        self.content = content
        self.youtube_link = youtube_link
        self.user_id = user_id
        self.created_at = created_at
        self.author = author

    @staticmethod
    def extract_youtube_id(url: str) -> str | None:
        """Extrai o ID do vídeo do YouTube de uma URL."""
        if not url:
            return None
        # Padrões Regex para diferentes formatos de URL do YouTube
        patterns = [
            r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/|)([\w-]{11})',
            r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/shorts/([\w-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None