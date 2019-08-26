var env = process.env;
var express = require('express');
var app = express();
var port = env.PORT || 3005;
var bodyParser = require('body-parser');
app.use(bodyParser.json());

app.post('/runtime-messages', function(req, res) {
    console.log('HttpSocketIO::log', req.body);
    res.send('Ok');
});

app.listen(port, function() {
    console.log('Example app listening on port ' + port);
});
