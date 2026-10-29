
from contextlib import contextmanager

from flask_sqlalchemy import SQLAlchemy as _SQAlchemy


class SQLAlchemy(_SQAlchemy):
    """重写Flask-SQLAlchemy中的核心类，实现自动提交"""

    # @contextmanager 用来快速实现快速写 `with` 上下文管理器
    # 作用:给一段代码块绑定【前置、后置、异常捕获逻辑】，类似于java的AOP 的环绕通知 `@Around`
    @contextmanager
    def auto_commit(self):
        try:
            yield  #  with 包裹的业务代码执行点
            self.session.commit()  # 业务代码跑完、没报错 → 提交事务
        except Exception as e:
            self.session.rollback()  # 只要抛出异常 → 回滚
            raise e  # 把异常继续往外抛，上层还能捕获处理
