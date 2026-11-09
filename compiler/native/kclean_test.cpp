#include "kparse.cpp"
#include <iostream>
int main(){try{
 const std::string s="func main[i64] { @p x:42;print(\"value ${x}\"..true);return 0; };";auto seed=parse_source(s.data(),s.size());if(!seed->diagnostics.empty())return 1;Checker(*seed).run();Verifier(*seed).run();unsigned count=1;Id format=0,concat=0;for(Id i=0;i<seed->arena.size();++i){if(seed->arena[i].kind=="format")format=i;if(seed->arena[i].kind=="concat")concat=i;}
 for(unsigned m=0;m<7;++m){Unit u=*seed;if(m==0)u.arena[format].type="i64";if(m==1)u.arena[format].children.clear();if(m==2)u.arena[concat].children.pop_back();if(m==3)u.arena[concat].type="bool";if(m==4)u.aesop_syntax=false;if(m==5)u.arena[format].value="forged";if(m==6){u.arena[concat].children[0]=u.arena[format].children[0];}serialize(u);const auto before=u.json;bool rejected=false;try{Verifier(u).run();}catch(const Failure &f){if(f.diagnostic.code!="E500")return 2;rejected=true;}serialize(u);if(!rejected||u.json!=before)return 3;++count;}
 std::cout<<"PASS "<<count<<" independent clean-syntax verifier cases\n";return 0;
}catch(const Failure &f){std::cerr<<f.diagnostic.message<<'\n';return 4;}}
