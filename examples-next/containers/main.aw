-- map<K,V> and set<T>, one api, owned by @s bindings, iterated with for
func main: i64 {
    -- text keys, integer values
    @s counts map<text,i64>: map.new<text,i64>(4);
    print(map.valid(counts));
    map.set(counts,"owl",1);
    map.set(counts,"cat",2);
    map.set(counts,"owl",3);
    print(map.length(counts));
    print(map.get(counts,"owl"));
    print(map.has(counts,"dog"));
    print(map.remove(counts,"cat"));
    print(map.remove(counts,"cat"));
    print(map.length(counts));

    -- text values and integer keys
    @s names map<i64,text>: map.new<i64,text>(2);
    map.set(names,7,"seven");
    map.set(names,9,"nine");
    print(map.get(names,9));
    @p name_vector vector<text>: map.values(names);
    print(vector.length(name_vector));

    -- iteration yields keys, in hash order, never a copy of the container
    @p total: 0;
    for key in counts {
        print(key);
        total: total + map.get(counts,key);
    };
    print(total);
    for id in names {
        print(id);
    };

    -- growing past the initial capacity keeps every key
    @s squares map<i64,i64>: map.new<i64,i64>(1);
    for n in 1..9 {
        map.set(squares,n,n * n);
    };
    print(map.length(squares));
    print(map.get(squares,8));

    -- sets share the same ownership and iteration rules
    @s seen set<text>: set.new<text>(2);
    print(set.add(seen,"alpha"));
    print(set.add(seen,"alpha"));
    print(set.add(seen,"beta"));
    print(set.length(seen));
    print(set.has(seen,"beta"));
    print(set.remove(seen,"beta"));
    print(set.length(seen));
    for item in seen {
        print(item);
    };

    -- clearing releases the keys and values the container owns
    map.clear(counts);
    print(map.length(counts));
    print(map.has(counts,"owl"));
    map.set(counts,"new",5);
    print(map.get(counts,"new"));

    -- integer sets from a workload
    @s marks set<i64>: set.new<i64>(4);
    for step in 0..12 {
        if step % 3 == 0 { set.add(marks,step); };
    };
    print(set.length(marks));
    @p marks_vector vector<i64>: set.values(marks);
    @p sum: 0;
    for mark in marks_vector {
        sum: sum + mark;
    };
    print(sum);
    print("containers done");
    return 0;
};
