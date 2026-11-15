import {LineChart,Line,BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer} from 'recharts';
export default function Trend({data,labels,color='#6B8A57',unit='',bar=false}:{data:(number|null)[];labels?:string[];color?:string;unit?:string;bar?:boolean}){
 const d=data.map((v,i)=>({w:labels?.[i]??('#'+(i+1)),v}));
 const tip=<Tooltip formatter={(v)=>v==null?'No observation':`${v}${unit}`}/>;
 if(!d.some(x=>x.v!=null))return <p className="src">No observations available for this period.</p>;
 return <div style={{height:140}}><ResponsiveContainer>{bar
  ?<BarChart data={d}><XAxis dataKey="w" fontSize={11}/><YAxis fontSize={11} width={34}/>{tip}<Bar dataKey="v" fill={color}/></BarChart>
  :<LineChart data={d}><XAxis dataKey="w" fontSize={11}/><YAxis fontSize={11} width={34} domain={['auto','auto']}/>{tip}<Line dataKey="v" stroke={color} dot={false} strokeWidth={2} connectNulls={false}/></LineChart>}</ResponsiveContainer></div>}
