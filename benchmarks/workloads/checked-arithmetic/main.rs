fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        std::process::exit(2);
    }
    let rounds: i64 = args[1].parse().unwrap();
    let factor: i64 = args[2].parse().unwrap();
    let mut state: i64 = args[3].parse().unwrap();
    let mut total: i64 = 0;
    for i in 0..rounds {
        state = (state * factor - i) % 1048573;
        total += state;
    }
    println!("{total}\n{state}");
}
