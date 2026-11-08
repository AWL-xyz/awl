struct Point
    x: i64
    y: i64
end
function shifted(p: Point, dx: i64) -> Point
    return Point(p.x + dx,p.y)
end
