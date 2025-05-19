"""
Visão Geral
|----| >>> Backend <<<
|    |---> app.py # Rotas principais e configurações Flask
|    |---> classes.py # Classes
|    |---> database.py # Conexão com SQLite e operações CRUD
|    |---> auth.py # Login, Registro, Auth
|
|----| >>> Static <<<
|    |---> css/ # Arquivos CSS (Boostrap)
|    |---> js/ # JavaScript (Interações frontend)
|    |---> images/ 
|
|----| >>> Templates <<<
|    |---> base.html 
|    |---> index.html
|    |---> register.html
|    |---> login.html
|    |----| >>> Admin <<<
|         |---> admin_dashboard


Funcionalidades Site
Autenticação:
    - Login/Logout com sessões
    - Registro de novos usuários
    - Níveis de acesso (usuário/admin)

Página Principal:
    - Listagem dinâmica de golpes (via API)
    - Carrossel com dicas de prevenção
    - Barra de busca funcional

Admin Dashboard:
    - Aprovar/remover denúncias
    - Gerenciar usuários
    - Estatísticas de golpes

Denúncia de Golpes:
    - Formulário com upload de evidências
    - Categorização automática (phishing, fake news, etc.)

"""











