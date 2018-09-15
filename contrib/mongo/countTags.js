//
// Report the number of times each tag is used
// See "Shell Example 2" at http://www.mongodb.org/display/DOCS/MapReduce
//
// Usage: mongo monitoring ./countTags.js

// map function
m = function() {
        this.tags.forEach(
            function(z) {
                emit( z, { count: 1 } );
            }
        );
    };

// reduce funtion
r = function( key, values) {
        var total = 0;
        for ( var i=0; i<values.length; i++ )
            total += values[i].count;
        return { count: total };
    };

res = db.alerts.mapReduce(m, r, { out: { inline: 1 }});

// different output formats
// res.find().forEach(function(f){print(tojson(f,'',true));});
res.find().forEach(function(f){print(f['value']['count'],f['_id']);});
