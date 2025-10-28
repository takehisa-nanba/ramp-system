# run.py (プロジェクトルート)

# create_app関数をインポート
from app.__init__ import create_app 

# Flask-Migrateがアプリケーションインスタンスを見つけられるよう、トップレベルで作成
app = create_app() 

app.config.from_object('app.config.Config')

if __name__ == '__main__':
    # Flaskサーバーの実行は通常通り
    app.run(debug=True)

def recreate_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database recreated successfully!")

