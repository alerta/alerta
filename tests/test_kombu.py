
from kombu import BrokerConnection, Exchange, Queue

media_exchange = Exchange("media", "direct", durable=True)
video_queue = Queue("video", exchange=media_exchange, routing_key="video")

def process_media(body, message):
    print body
    message.ack()

# connections
with BrokerConnection("amqp://guest:guest@localhost//") as conn:

    # Declare the video queue so that the messages can be delivered.
    # It is a best practice in Kombu to have both publishers and
    # consumers declare the queue.
    video_queue(conn.channel()).declare()

    # produce
    with conn.Producer(exchange=media_exchange,
                       serializer="json", routing_key="video") as producer:
        producer.publish({"name": "/tmp/lolcat1.avi", "size": 1301013})

    # consume
    with conn.Consumer(video_queue, callbacks=[process_media]) as consumer:
        # Process messages and handle events on all channels
        while True:
            conn.drain_events()

# Consume from several queues on the same channel:
video_queue = Queue("video", exchange=media_exchange, key="video")
image_queue = Queue("image", exchange=media_exchange, key="image")

with connection.Consumer([video_queue, image_queue],
                         callbacks=[process_media]) as consumer:
    while True:
        connection.drain_events()