import geometry.points as geo
union Result
    Value(point: geo.Point)
    Empty()
end
function make() -> Result
    return Result.Value(geo.Point(3,4))
end
