namespace Awl_format {
Result source(std::string_view input,const std::string &label,bool json) {
    auto unit=parse_source(input.data(),input.size());
    if(!unit->diagnostics.empty()) return {{},render(*unit,label,json)};

    // The parser identifies actual declarations, match arms, and imports.
    // In particular, i64.match(...) isn't a block opener and an unquoted
    // import path may contain components that spell keywords.
    enum class Mark { Plain, Enum, Match, Arm, Import };
    std::vector<Mark> marks(unit->tokens.size(),Mark::Plain);
    for(const auto &node:unit->arena) {
        if(node.kind=="union") marks.at(node.token)=Mark::Enum;
        else if(node.kind=="match") marks.at(node.token)=Mark::Match;
        else if(node.kind=="case") marks.at(node.token)=Mark::Arm;
        else if(node.kind=="import") marks.at(node.token)=Mark::Import;
    }

    // Keep every non-trivia byte in place. Closing delimiters and case
    // labels at the start of a line align with the construct they close.
    enum class Level { Brace, Paren, Bracket, Enum, Match, Arm };
    std::vector<Level> levels;
    auto pop=[&](Level expected) {
        if(levels.empty()||levels.back()!=expected) throw std::logic_error("unbalanced formatter layout");
        levels.pop_back();
    };
    std::string output;output.reserve(input.size());
    size_t offset=0,token=0;
    uint32_t line=1;
    bool in_import=false;
    while(offset<input.size()) {
        const auto lf=input.find('\n',offset);
        auto contents=input.substr(offset,lf==std::string_view::npos?input.size()-offset:lf-offset);
        offset=lf==std::string_view::npos?input.size():lf+1;
        const auto left=contents.find_first_not_of(" \t\r");
        if(left!=std::string_view::npos) contents=contents.substr(left,contents.find_last_not_of(" \t\r")-left+1);
        else contents={};

        auto indent=levels.size();bool leading=true;
        for(;token+1<unit->tokens.size()&&unit->tokens[token].line==line;++token) {
            const auto &t=unit->tokens[token];
            const auto text=input.substr(unit->bytes[t.start],unit->bytes[t.end]-unit->bytes[t.start]);
            const auto mark=marks[token];
            if(mark==Mark::Import) in_import=true;
            if(in_import) {if(text==";") in_import=false;leading=false;continue;}
            if(text=="}") pop(Level::Brace);
            else if(text==")") pop(Level::Paren);
            else if(text=="]") pop(Level::Bracket);
            else if(text=="end") {
                if(!levels.empty()&&levels.back()==Level::Arm) pop(Level::Arm);
                pop(!levels.empty()&&levels.back()==Level::Enum?Level::Enum:Level::Match);
            } else if(mark==Mark::Arm) {
                if(!levels.empty()&&levels.back()==Level::Arm) pop(Level::Arm);
                if(levels.empty()||levels.back()!=Level::Match) throw std::logic_error("case outside formatter match");
                if(leading) indent=levels.size();
                levels.push_back(Level::Arm);leading=false;
                continue;
            } else {
                if(text=="{") levels.push_back(Level::Brace);
                else if(text=="(") levels.push_back(Level::Paren);
                else if(text=="[") levels.push_back(Level::Bracket);
                else if(mark==Mark::Enum) levels.push_back(Level::Enum);
                else if(mark==Mark::Match) levels.push_back(Level::Match);
                leading=false;
                continue;
            }
            if(leading) indent=levels.size();
        }
        const size_t spaces=contents.empty()?0:indent*4;
        if(spaces+contents.size()+1>Awl_package::source_limit-output.size())
            throw std::runtime_error("formatted source would exceed 1 MiB: "+label);
        if(!contents.empty()) {output.append(spaces,' ');output.append(contents);}
        output+='\n';
        ++line;
    }
    if(!levels.empty()||in_import) throw std::logic_error("unclosed formatter layout");
    return {std::move(output),{}};
}
}
