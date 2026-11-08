struct Greeting
    text: string
end
function decorate(value: string) -> Greeting
    return Greeting("Hello, " + value + "!")
end
function main() -> i64
    local name: string = "Awl \u{1F680}"
    local message: Greeting = decorate(name)
    print(message.text)
    print(string_length(name))
    print(string_bytes(name))
    print(string_slice(name,string_length("Awl "),1))
    print(name == "Awl 🚀")
    print("Answer: " + string_from_i64(42))
    return 0
end
