import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.extensions import db
from backend.app import create_app
from backend.app.models.masters.master_definitions import StatusMaster

def add_statuses():
    app = create_app()
    with app.app_context():
        statuses = [
            {'name': '問い合わせ', 'description': '利用前の見込み客や問い合わせ段階', 'sort_order': 1},
            {'name': '利用中', 'description': '現在サービスを利用している状態', 'sort_order': 2},
            {'name': '利用終了（定着支援中）', 'description': '就職し、6か月の定着支援期間中', 'sort_order': 3},
            {'name': '利用終了（定着完了）', 'description': '6か月の定着支援が完了した状態', 'sort_order': 4},
            {'name': '利用終了（退所）', 'description': '就職以外の理由で利用を終了した状態', 'sort_order': 5},
        ]
        
        for status_data in statuses:
            status = StatusMaster.query.filter_by(name=status_data['name']).first()
            if not status:
                print(f"Adding status: {status_data['name']}")
                new_status = StatusMaster(
                    name=status_data['name'],
                    description=status_data['description'],
                    sort_order=status_data['sort_order']
                )
                db.session.add(new_status)
            else:
                print(f"Updating status: {status_data['name']}")
                status.description = status_data['description']
                status.sort_order = status_data['sort_order']
        
        db.session.commit()
        print("Status update complete.")

if __name__ == '__main__':
    add_statuses()
