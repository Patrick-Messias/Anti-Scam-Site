import pytest, sys
sys.path.append('C:\\Users\\Patrick\\Documents\\FACULDADE\\PROJETO INTEGRADOR\\FINAL')
from app import create_app # type: ignore

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Banco em memória para testes
    
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    return app.test_client()