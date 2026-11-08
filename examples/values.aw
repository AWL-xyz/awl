-- Value structs copy on assignment and calls; no references are involved.
struct Point
    x: i64
    y: i64
end

struct Particle
    position: Point
    ticks: u64
    active: bool
end

function advance(p: Particle, dx: i64) -> Particle
    p.position.x = p.position.x + dx
    p.ticks = p.ticks + 1u64
    return p
end

function main() -> i64
    local first: Particle = Particle(Point(10, 20), 0u64, true)
    local next: Particle = advance(first, 5)
    print(first.position.x)
    print(next.position.x)
    print(next.ticks)
    print(next.active)
    print(18446744073709551615u64)
    return 0
end
