from __future__ import annotations  # Pra referencia circular
from typing import TYPE_CHECKING
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

if TYPE_CHECKING: from database import Database  # type: ignore # Para type hints apenas

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

class Site(ClassUtils):
    def __init__(self, name: str, url: str):
        super().__init__()
        self.name = name
        self.url = url

    @classmethod
    def validate_url(cls, url: str) -> bool:
        return url.startswith(('http://', 'https://'))


class User(ClassUtils, UserMixin):
    def __init__(self, id, name, email, password_hash, type_user='noob',
                 confidence=1.0, age=None, city=None, state=None, civil_state=None):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = password_hash  # Note que é password_hash, não password
        self.type_user = type_user
        self.confidence = confidence
        self.age = age
        self.city = city
        self.state = state
        self.civil_state = civil_state

    def permissions_set(self):
        self.can_check_tutorials = self.confidence >= 1.0
        self.can_register_scam = self.confidence >= 1.0
        self.can_approve_scam = self.confidence >= 2.0

    def report_scam(self, name: str, site: Site, type_scam: str, evidence: str) -> DigitalScam:
        if not self.can_register_scam:
            raise PermissionError("User lacks permissions to report scams.")
        return DigitalScam(name, site, type_scam, 0.0, 0.0, evidence, self)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class UserNoob(User):
    def __init__(self, name, type_user, email, age, city, state, civil_state):
        super().__init__(name=name, 
                        type_user=type_user, 
                        email=email, 
                        confidence=1.0,
                        age=age, 
                        city=city, 
                        state=state, 
                        civil_state=civil_state)

class UserExpert(User):
    def __init__(self, name, type_user, email, age, city, state, civil_state):
        super().__init__(name=name, 
                        type_user=type_user, 
                        email=email, 
                        confidence=2.0,
                        age=age, 
                        city=city, 
                        state=state, 
                        civil_state=civil_state)

class Admin(User):
    def __init__(self, id, name, email, password):
        super().__init__(id, name, email, password, confidence=3.0, is_admin=True)



class DigitalScam(ClassUtils):
    def __init__(self, name: str, site: Site, type_scam: str,
                 danger_level: float, damage_level: float,
                 evidence: str, user: User):
        super().__init__()
        self.name = name
        self.site = site
        self.type_scam = type_scam
        self.danger_level = danger_level
        self.damage_level = damage_level
        self.evidence = evidence
        self.user = user

class Tutorial(ClassUtils):
    def __init__(self,
                 title: str,
                 difficulty_level: str,
                 author: User,
                 data,
                 ):
        super().__init__()
        self.title = title
        self.difficulty_level = difficulty_level
        self.author = author
        self.data = data



class MainSite(ClassUtils):
    _instance = None  # Singleton
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self.reported_scams = []
        self.tutorials = []
    
    def add_scam(self, scam: DigitalScam):
        self.reported_scams.append(scam)
    
    def get_scams_by_type(self, type_scam: str) -> list:
        return [s for s in self.reported_scams if s.type_scam == type_scam]

    @classmethod
    def get_instance(cls) -> 'MainSite':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

'''
    @classmethod
    def create_admin(cls, name: str, email: str) -> 'User':
        return cls(name=name, email=email, confidence=3.0)
'''

if __name__ == '__main__':
    print("Este módulo contém apenas definições de classes.")













































