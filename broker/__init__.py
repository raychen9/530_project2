def __init__(self):
    self.client = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
        socket_keepalive=True,
        socket_connect_timeout=10,
        retry_on_timeout=True,
    )