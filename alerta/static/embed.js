(function($, window) {

  var config = {
    endpoint: 'http://api.alerta.io',
    key: null
  };

  var Alerta = function() {};
  Alerta.prototype = {
    defaults: {}
  }
  $.alerta = new Alerta();

  $.fn.alerta = function( url, options ) {

    $.extend(config, $.alerta.defaults, options);

    return this.each(function() {

      var base = config.endpoint + '/oembed?url=' + encodeURIComponent(url);
      var key = (config.key ? '&api-key=' + config.key : '');
      var title = (config.title ? '&title=' + encodeURIComponent(config.title) : '');
      base += key + title;

      $.ajax({
        url: base,
        context: this,
        success: function(data) {
          $(this).html(data.html);
        }
      });
    });
  }

  window.Alerta = Alerta;
}(jQuery, window));
