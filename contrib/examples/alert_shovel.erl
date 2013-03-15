[{rabbitmq_shovel,
  [{shovels,
    [{alerts_shovel,
      [{sources, [{broker,"amqp://10.121.75.193"}]},
      {destinations, [{broker, "amqp://192.168.16.66"}]},
      {queue, <<"alerts">>},
      {ack_mode, on_confirm},
      {publish_properties, [{delivery_mode, 2}]},
      {publish_fields, [{exchange, <<"">>},
                         {routing_key, <<"alerts">>}]},
      {reconnect_delay, 5}
      ]}
     ]
   }]
}].
