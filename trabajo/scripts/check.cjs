const ARS = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 });
const ARSM = new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', notation: 'compact', maximumFractionDigits: 1 });
const NUM = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });
const PCT = v => (v > 0 ? '+' : '') + v.toLocaleString('es-AR', { maximumFractionDigits: 1 }) + '%';

const MESES = ['2025-01','2025-02','2025-03','2025-04','2025-05','2025-06','2025-07','2025-08','2025-09','2025-10','2025-11','2025-12','2026-01','2026-02','2026-03','2026-04','2026-05','2026-06','2026-07','2026-08','2026-09'];
const ML = m => { const [y, mm] = m.split('-'); return ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][+mm - 1] + ' ' + y.slice(2); };
const MENSUAL = { // ventas, unidades, tickets (total empresa)
  '2025-01':[23276875,12182.1,2415],'2025-02':[24481813,12577.5,2145],'2025-03':[28330750,13330.85,2671],'2025-04':[31754511,13878.1,2552],
  '2025-05':[29173371,12012.24,2559],'2025-06':[28661969,11667.25,2546],'2025-07':[32341704,13253.36,2817],'2025-08':[32744802,12647,2868],
  '2025-09':[29936424,10604.6,2511],'2025-10':[36595121,12353.98,2784],'2025-11':[43843487,13778.75,3091],'2025-12':[40908095,13276.81,3056],
  '2026-01':[47890670,15546.86,3526],'2026-02':[47781020,16031.91,3685],'2026-03':[41183790,12883.05,3181],'2026-04':[37232476,12252.03,2702],
  '2026-05':[35942628,11827.77,2626],'2026-06':[36848331,10864.45,2652],'2026-07':[49782168,13970.25,2926],'2026-08':[37243385,10610.4,2544],
  '2026-09':[41029496,11920.53,2436]
};
const LUGARES = ['Carlos Paz','Villa Allende','Dietetica','Cordoba','Villa General Belgrano'];
const LUGAR_LBL = { 'Dietetica': 'Dietética (mayorista)', 'Cordoba': 'Córdoba' };
const POR_LUGAR = [["2025-01","Carlos Paz",12297111],["2025-01","Dietetica",5359826],["2025-01","Villa Allende",5619938],["2025-02","Carlos Paz",12141321],["2025-02","Dietetica",7262745],["2025-02","Villa Allende",5077747],["2025-03","Carlos Paz",15778533],["2025-03","Dietetica",6478495],["2025-03","Villa Allende",6073722],["2025-04","Carlos Paz",15263099],["2025-04","Dietetica",8717824],["2025-04","Villa Allende",7773588],["2025-05","Carlos Paz",14699014],["2025-05","Dietetica",6094515],["2025-05","Villa Allende",8379842],["2025-06","Carlos Paz",14984637],["2025-06","Dietetica",5667539],["2025-06","Villa Allende",8009793],["2025-07","Carlos Paz",16056716],["2025-07","Dietetica",7914807],["2025-07","Villa Allende",8370181],["2025-08","Carlos Paz",15708057],["2025-08","Dietetica",7019988],["2025-08","Villa Allende",10016757],["2025-09","Carlos Paz",14148151],["2025-09","Dietetica",6293310],["2025-09","Villa Allende",9494963],["2025-10","Carlos Paz",13521025],["2025-10","Cordoba",7311038],["2025-10","Dietetica",7077024],["2025-10","Villa Allende",8686034],["2025-11","Carlos Paz",16284574],["2025-11","Cordoba",12902127],["2025-11","Dietetica",6837931],["2025-11","Villa Allende",7818855],["2025-12","Carlos Paz",17378979],["2025-12","Cordoba",5432372],["2025-12","Dietetica",8972548],["2025-12","Villa Allende",9124196],["2026-01","Carlos Paz",23757178],["2026-01","Cordoba",4588279],["2026-01","Dietetica",12178373],["2026-01","Villa Allende",7366840],["2026-02","Carlos Paz",24148225],["2026-02","Cordoba",5365301],["2026-02","Dietetica",10588969],["2026-02","Villa Allende",7678525],["2026-03","Carlos Paz",19445418],["2026-03","Cordoba",3616750],["2026-03","Dietetica",9733905],["2026-03","Villa Allende",8387717],["2026-04","Carlos Paz",19552717],["2026-04","Dietetica",9016055],["2026-04","Villa Allende",8663704],["2026-05","Carlos Paz",18565613],["2026-05","Dietetica",7527299],["2026-05","Villa Allende",9849716],["2026-06","Carlos Paz",18368555],["2026-06","Dietetica",7448521],["2026-06","Villa Allende",11031255],["2026-07","Carlos Paz",25834469],["2026-07","Dietetica",11403556],["2026-07","Villa Allende",12544143],["2026-08","Carlos Paz",18925242],["2026-08","Dietetica",7032503],["2026-08","Villa Allende",11285640],["2026-09","Carlos Paz",21926039],["2026-09","Dietetica",6592982],["2026-09","Villa Allende",11733078],["2026-09","Villa General Belgrano",777397]];
const Q3 = [ // lugar: ventas act/ant, unidades act/ant, tickets act/ant
  ['Carlos Paz', 66685750, 45912924, 16538.7, 15433.4, 4928, 4936],
  ['Villa Allende', 35562861, 27881901, 7735.1, 9177.2, 2694, 2987],
  ['Dietetica', 25029041, 21228105, 11968.4, 11894.4, 219, 273],
  ['Total', 128055049, 95022930, 36501.2, 36505.0, 7906, 8196]
];
const CAT = [ // categoría: ventas act/ant, unidades act/ant (3T 2026 vs 3T 2025)
  ['Facturas',25638066,14402733,18215,16585],['Otros',39672091,28126358,6898,6922],['Panadería',10560578,7062015,2325,2915],
  ['Pastas',12049284,9412919,1472,1517],['Pan Molde',9251381,6657862,1388,1341],['Budines',5309902,3852259,735,846],
  ['Chipa',6348617,4908173,631,450],['Criollos',4554637,3731032,577,452],['Alfajores',2159940,1419466,856,639],
  ['Pizzetas',1618009,1403915,716,698],['Pan Sandwich',3576889,4993262,1223,1818],['Cuadrados',3692989,4128810,807,1187],
  ['Cookies',1233185,1751370,277,544],['Postres',1113521,1322521,183,309],['Tortas',487460,1091859,19,48]
];
const MIX = [['1 producto',13490,6060],['2 productos',10311,10424],['3 o más',9586,22276]];
const DIAS = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'];
const HORAS = [9,10,11,12,13,14,15,16,17,18,19,20];
const HEAT = [
  [127,257,253,245,178,16,1,289,616,787,677,239],
  [335,493,567,548,310,24,4,324,632,889,639,219],
  [350,522,569,556,312,27,16,352,652,846,721,203],
  [321,468,559,476,318,19,1,343,702,826,712,222],
  [362,577,619,657,357,22,7,423,754,1007,852,289],
  [383,710,1007,1066,514,20,2,424,756,929,862,295],
  [195,487,606,650,272,5,5,48,84,88,54,37]
];
const INACT = [
  ['Dulce Miga',121,'cada 2,1 días',19151012],['Cliente particular P.C.',92,'cada 9,9 días',4506884],
  ['Cliente particular G.L.',93,'cada 18 días',2336750],['Alma Light',92,'cada 17,3 días',1565306],
  ['Canela y Miel',169,'cada 21,9 días',1472473],['Mdoce S.A.S.',153,'cada 15 días',700430],['CAPE SRL',132,'cada 3,8 días',687139]
];
const CANASTA = [
  ['Criollos + Medialunas',2060,'1,2'],['Criollos + Chipa',1192,'1,2'],['Medialunas + Facturas',540,'1,4'],
  ['Cuadrados surtidos entre sí (limón, naranja, coco, membrillo, manzana: 5 pares)',448,'4,6 a 8,6'],
  ['Sorrentinos de Calabaza + Sorrentinos de Ternera y Verduras',293,'55,9'],['Medialunas + Café con leche chico',228,'1,3'],
  ['Talitas con semillas + Talitas sin semillas',165,'7,8'],['Chipa + Café con leche chico',151,'1,5'],
  ['Pizza de Muzzarella + Pizza de Muzzarella y Jamón',119,'11,0'],['Alfajor Chocolate Blanco + Alfajor Chocolate Negro',80,'29,2']
];
const SEMANAL = {"semanas":["2026-07-13","2026-07-20","2026-07-27","2026-08-03","2026-08-10","2026-08-17","2026-08-24","2026-08-31","2026-09-07","2026-09-14","2026-09-21","2026-09-28","2026-10-05"],"lugares":{"Carlos Paz":[["Medialunas",[1187700,1052035,810150,608240,827820,660970,752350,772110,948580,720845,701270,873510,861690],[738.0,652.0,514.0,390.0,510.0,428.0,469.0,509.0,581.0,437.0,420.0,500.0,501.0]],["Chipa",[344340,432720,283820,224795,245940,304510,350320,366675,469068,403392,418480,356159,382574],[30.6,39.0,25.9,19.8,22.1,26.9,31.1,36.7,57.2,47.1,49.5,46.3,49.8]],["Criollos",[387820,263830,168660,248440,229301,212110,218582,267059,308580,362705,245660,286229,352632],[41.7,28.7,18.5,26.8,24.5,23.0,23.6,37.5,55.4,60.3,33.5,47.8,53.5]],["Masas Pan Frances",[356270,245880,265270,196760,272850,224190,239075,209190,263924,219073,239150,231000,359030],[63.7,43.3,48.4,35.3,48.1,41.3,43.5,39.0,46.5,39.6,42.6,40.0,63.1]],["Pan Molde Integral",[289520,170940,193270,147070,150920,112420,86240,205090,223750,260200,192560,237660,272770],[42.0,25.0,27.0,21.0,21.0,16.0,12.0,30.0,32.0,38.0,27.0,31.0,36.0]],["Sorrentinos de Calabaza",[202300,66300,323000,231200,68000,170000,81600,141100,137700,15300,79280,122000,193800],[13.0,4.0,21.0,15.0,5.0,11.0,6.0,9.0,10.0,1.0,6.0,8.0,12.0]],["pan de campo",[200380,94600,127280,97180,176300,145340,137600,99760,126100,138240,153600,117120,206400],[28.0,14.0,18.0,14.0,23.0,20.0,20.0,14.0,18.0,17.0,19.0,14.0,23.0]],["Pan Molde Blanco",[125250,103125,84000,121500,76500,108750,77250,118960,189980,226470,151270,192460,214090],[19.0,16.0,13.0,20.0,11.0,17.0,13.0,20.0,27.0,33.0,22.0,27.0,30.0]],["Sorrentinos de Jamon y Queso",[96900,207400,30600,168300,108800,57800,122400,64600,137700,120700,11900,62900,124100],[6.0,13.0,2.0,11.0,8.0,4.0,9.0,4.0,9.0,8.0,1.0,4.0,8.0]],["Sorrentinos de Ternera y Verduras",[66300,51000,137700,202300,56100,158100,81600,108800,57800,0,17000,45900,163200],[4.0,3.0,9.0,13.0,4.0,10.0,6.0,7.0,4.0,0,1.0,3.0,10.0]],["Sandwich de Miga Jamon y Queso",[96600,5400,95400,37800,37800,61200,70800,71400,130250,170300,87750,48750,178750],[17.0,1.0,18.0,7.0,7.0,11.0,13.0,14.0,23.0,28.0,15.0,8.0,30.0]],["Facturas",[0,0,0,0,0,0,0,98700,168300,205500,219000,195150,184800],[0,0,0,0,0,0,0,73.0,127.0,149.0,163.0,141.0,133.0]],["ravioles pollo verdura",[96900,110500,78200,47600,119000,34000,11900,124100,17000,71400,102000,66300,125800],[7.0,7.0,5.0,3.0,10.0,2.0,1.0,8.0,1.0,6.0,7.0,5.0,8.0]],["Pizzetas x2",[89000,62000,67000,62000,56000,90000,23000,91500,125500,111000,65000,69400,43800],[38.0,30.0,30.0,30.0,26.0,40.0,10.0,42.0,50.0,42.0,30.0,28.0,16.0]],["Pizza de Muzzarella",[120000,80250,44250,42000,105750,36750,51750,55500,90000,39000,30750,118500,63000],[17.0,13.0,6.0,6.0,19.0,5.0,8.0,10.0,13.0,6.0,5.0,18.0,9.0]],["Talitas con Semillas",[30210,75790,43460,55915,76850,60420,54060,12500,19000,53550,73750,94750,137500],[6.0,16.0,9.0,12.0,16.0,12.0,11.0,3.0,4.0,11.0,15.0,17.0,24.0]],["Cuadrado de Limon",[61000,74000,52000,48000,35500,27000,40500,37800,86100,78000,65900,95500,85400],[13.0,16.0,12.0,11.0,8.0,6.0,9.0,9.0,22.0,17.0,16.0,23.0,20.0]],["Budin de Limon",[97600,20800,20800,23200,85600,53600,92800,52000,77450,75950,33750,94150,36850],[13.0,3.0,3.0,3.0,11.0,7.0,13.0,8.0,11.0,10.0,5.0,13.0,5.0]],["Budin de Zanahoria",[43200,75600,58500,122400,0,43200,62100,58300,50500,100700,59050,26600,45600],[5.0,9.0,7.0,14.0,0,5.0,8.0,8.0,6.0,12.0,7.0,3.0,5.0]],["Talitas sin Semillas",[47000,25750,81500,70500,64000,37000,26500,12500,19000,63600,102100,95300,79100],[10.0,6.0,18.0,15.0,14.0,8.0,6.0,3.0,4.0,13.0,20.0,18.0,15.0]]],"Villa Allende":[["Medialunas",[247965,195870,191460,235960,224140,204255,127990,195450,288000,263520,212510,230400,362760],[156.0,122.0,128.0,146.0,136.0,133.0,77.0,119.0,163.0,147.0,115.0,129.0,194.0]],["Masas Pan Frances",[204385,181648,165541,140729,205666,219416,244655,201698,188619,228049,232952,216054,181153],[37.3,33.5,30.6,24.5,37.0,39.6,44.3,36.2,33.2,40.8,40.2,38.6,32.5]],["Pan de Campo 450gr",[153940,145770,118680,105780,174580,122120,167700,77830,191450,142080,156480,256320,221280],[21.0,19.0,17.0,14.0,23.0,16.0,23.0,10.0,24.0,17.0,18.0,30.0,25.0]],["Pan Molde Integral",[184800,140140,114730,127820,125510,103180,68530,155540,159180,196620,266220,173130,167910],[27.0,20.0,17.0,18.0,18.0,15.0,10.0,22.0,21.0,25.0,37.0,23.0,21.0]],["FACTURAS X 2 BOLSITA",[93375,129500,105250,128500,108250,90000,276750,137000,152190,215020,157170,163680,163680],[40.0,54.0,45.0,55.0,46.0,38.0,118.0,59.0,58.0,76.0,55.0,57.0,55.0]],["Chipa",[88791,109926,92523,75480,79793,80949,147430,83120,116290,169315,139936,134245,163650],[8.9,10.7,9.6,7.2,7.9,7.9,14.1,7.9,11.3,16.4,13.3,13.3,15.8]],["Pan Molde Blanco",[60000,96000,62250,106500,104250,114000,108750,90000,137350,149600,181050,120700,119850],[9.0,15.0,9.0,16.0,16.0,17.0,17.0,14.0,19.0,20.0,25.0,17.0,16.0]],["Criollos",[50102,69474,41266,70357,52418,39327,59468,38470,104464,52630,54550,54680,71900],[5.3,7.6,4.4,7.3,5.5,4.2,6.3,4.1,10.8,5.6,5.6,5.9,7.6]],["Sandwich de Miga Jamon y Queso",[72600,63900,0,27000,67200,5400,20400,70200,129825,124800,54600,20800,79300],[14.0,12.0,0,5.0,13.0,1.0,4.0,13.0,23.0,21.0,9.0,4.0,13.0]],["empanadas",[93450,0,156800,29050,45500,29400,36750,97300,0,56000,57600,16000,93000],[28.0,0,47.0,9.0,14.0,9.0,11.0,29.0,0,14.0,15.0,4.0,25.0]],["Cafe grande con o sin leche",[50050,38850,49000,30100,47950,57050,58100,42100,74800,34800,45600,46000,72000],[15.0,12.0,15.0,9.0,14.0,17.0,18.0,12.0,20.0,9.0,12.0,12.0,19.0]],["Sorrentinos de Ternera y Verduras",[30600,59500,52700,47600,86700,30600,47600,29750,146200,13600,11900,15300,49300],[2.0,4.0,4.0,3.0,6.0,2.0,4.0,2.0,10.0,1.0,1.0,1.0,3.0]],["Cuadrado de Limon",[62500,30500,26500,36000,50000,49500,40000,47500,35500,58000,41000,31000,65500],[14.0,7.0,6.0,8.0,11.0,11.0,9.0,10.0,8.0,13.0,9.0,7.0,14.0]],["Pizza de Muzzarella",[92250,35250,31500,66750,39750,33750,38250,42375,27000,21000,54000,45750,20250],[14.0,5.0,5.0,9.0,6.0,5.0,6.0,7.0,4.0,3.0,8.0,7.0,3.0]],["Pizzetas x2",[51250,40500,43000,63000,34500,23500,33500,34000,29600,40200,27300,49800,44400],[24.0,18.0,20.0,26.0,16.0,10.0,16.0,16.0,12.0,16.0,10.0,18.0,16.0]],["cafe + 2 medialunas",[43560,18480,37620,33000,19800,25740,5940,12540,13600,94500,33600,59500,114800],[7.0,3.0,6.0,5.0,3.0,4.0,1.0,2.0,2.0,14.0,5.0,9.0,17.0]],["Cuadrado de Coco con Dulce de Leche",[59950,4950,39600,56650,46200,9900,35200,47025,24750,53350,29700,38500,40150],[12.0,1.0,8.0,11.0,9.0,2.0,7.0,9.0,5.0,11.0,6.0,8.0,8.0]],["Cafe con o sin leche chico",[32400,23400,33900,25800,45300,38400,20400,54500,38500,57050,37450,33250,29750],[11.0,8.0,12.0,9.0,16.0,13.0,7.0,17.0,12.0,17.0,11.0,10.0,9.0]],["Spaguettis de Huevo 400gr",[25650,15200,13300,50350,78850,49400,39900,49875,0,44650,0,51300,8550],[3.0,2.0,2.0,6.0,10.0,6.0,5.0,6.0,0,6.0,0,6.0,1.0]],["Budin de Naranja",[14800,34400,15200,43200,28000,15200,65600,28800,39100,61200,56100,15300,8500],[2.0,5.0,2.0,6.0,4.0,2.0,10.0,4.0,5.0,8.0,7.0,2.0,1.0]]],"Dietetica":[["Medialunas",[1463820,1045199,634510,343763,1194178,388631,432321,1087104,398081,954806,729634,30942,254522],[1249.0,1092.0,584.0,306.0,1122.0,326.0,346.0,998.0,384.0,851.0,694.0,24.0,198.0]],["Sorrentinos de Jamon y Queso",[618182,112397,0,0,134876,0,112397,13600,112397,33719,67438,112397,112397],[55.0,10.0,0,0,12.0,0,10.0,1.0,10.0,3.0,6.0,10.0,10.0]],["Pan de Lomo x2",[275297,67835,79140,90447,129413,75373,119992,22612,53157,172053,64785,115174,157627],[144.0,36.0,42.0,48.0,67.0,40.0,62.0,12.0,24.0,76.0,30.0,52.0,69.0]],["Sorrentinos de Ternera y Verduras",[494545,126447,0,25289,112397,0,89917,0,112397,0,236033,0,11240],[44.0,11.0,0,2.0,10.0,0,8.0,0,10.0,0,21.0,0,1.0]],["Pan Molde Blanco",[102793,68826,56876,50207,79587,39917,98628,46711,57024,62520,103770,76500,90423],[18.0,12.0,10.0,9.0,15.0,7.0,17.0,9.0,10.0,11.0,17.0,10.0,14.0]],["Cuadrado de Brownie",[99175,47604,63472,0,63472,31736,43637,130910,11901,23802,47604,47603,115041],[25.0,12.0,16.0,0,16.0,8.0,11.0,33.0,3.0,6.0,12.0,12.0,29.0]],["Pan Molde Integral",[78756,32455,31207,25047,72800,64934,81531,43935,20025,33822,82024,47454,90422],[14.0,6.0,5.0,4.0,12.0,12.0,14.0,8.0,3.0,5.0,13.0,8.0,14.0]],["PAN DE MIGA",[148761,109092,29752,69422,19834,49587,9917,89256,19835,39670,9917,0,31736],[15.0,11.0,3.0,7.0,2.0,5.0,1.0,9.0,2.0,4.0,1.0,0,3.0]],["Postre(Lingote) Balcarce",[189817,111271,52364,19636,19636,39272,0,39273,13091,65455,19636,0,39272],[29.0,17.0,8.0,3.0,3.0,6.0,0,6.0,2.0,10.0,3.0,0,6.0]],["Postre (Lingote) Mini Marquise",[196364,26182,32727,0,19636,19636,0,47455,32891,78546,13091,0,104727],[30.0,4.0,5.0,0,3.0,3.0,0,7.0,4.0,12.0,2.0,0,16.0]],["Sorrentinos de Cordero",[343801,0,0,0,0,0,0,0,0,0,0,198347,0],[26.0,0,0,0,0,0,0,0,0,0,0,15.0,0]],["CHESCAKE INDIVIDUAL",[98182,98181,39273,13091,0,39272,0,39273,13091,13091,0,19636,104727],[15.0,15.0,6.0,2.0,0,6.0,0,6.0,2.0,2.0,0,3.0,16.0]],["Pan Arabe x 1",[45223,22612,0,22612,22612,45224,0,82909,0,26579,62709,0,132893],[24.0,12.0,0,12.0,12.0,24.0,0,44.0,0,12.0,29.0,0,60.0]],["Masas Pan Frances",[23288,37460,19835,0,58884,24436,45714,31567,26658,54022,51805,22185,29514],[4.9,7.7,4.1,0,12.2,5.1,8.7,6.6,5.6,11.2,10.8,4.7,6.1]],["Fetuchinis de Huevo 200gr",[144232,0,0,0,8000,13224,41058,3306,33058,72728,0,0,105256],[43.0,0,0,0,2.0,4.0,12.0,1.0,10.0,22.0,0,0,31.0]],["Discos Empanadas Arabes",[90710,0,75873,0,64793,0,64793,7160,0,99360,4562,0,9124],[28.0,0,23.0,0,20.0,0,20.0,2.0,0,18.0,1.0,0,2.0]],["Delivery",[60749,10959,31836,15918,37836,36795,27918,35754,9257,26216,26877,14877,21918],[12.0,2.0,6.0,3.0,7.0,7.0,6.0,8.0,2.0,5.0,5.0,3.0,4.0]],["Budin de Limon",[51200,0,30889,6400,12800,23378,6400,81560,0,6800,6800,101157,0],[8.0,0,5.0,1.0,2.0,4.0,1.0,15.0,0,1.0,1.0,18.0,0]],["Alfajor Chocolate Negro",[49984,0,13620,7140,26115,17851,0,69619,8926,17851,24991,44627,37486],[28.0,0,7.0,4.0,14.0,10.0,0,39.0,5.0,10.0,14.0,25.0,21.0]],["Cuadrado de Coco con Dulce de Leche",[43636,0,14545,19495,25455,10909,0,61818,0,18182,10909,72727,0],[12.0,0,4.0,5.0,7.0,3.0,0,17.0,0,5.0,3.0,20.0,0]]],"Todas":[["Medialunas",[2899485,2293104,1636120,1187963,2246138,1253856,1312661,2054664,1634661,1939171,1643414,1134852,1478972],[2143.0,1866.0,1226.0,842.0,1768.0,887.0,892.0,1626.0,1128.0,1435.0,1229.0,653.0,893.0]],["Masas Pan Frances",[583943,464988,450646,337489,537400,468042,529444,442455,479201,501144,523907,469239,569697],[105.9,84.4,83.2,59.9,97.3,85.9,96.5,81.8,85.3,91.6,93.7,83.2,101.7]],["Chipa",[435531,542646,376343,300275,325733,385459,500626,449795,610052,572707,572631,498483,546224],[39.7,49.7,35.5,27.1,30.0,34.8,45.5,44.6,70.8,63.4,64.1,60.5,65.6]],["Pan Molde Integral",[553076,343535,339207,299937,349230,280534,236301,404565,402955,490642,540804,458244,531102],[83.0,51.0,49.0,43.0,51.0,43.0,36.0,60.0,56.0,68.0,77.0,62.0,71.0]],["Criollos",[469571,346615,221890,322521,308716,256092,296202,329802,417275,442837,322971,340909,430879],[51.0,37.9,24.4,34.6,33.4,27.7,32.0,44.6,66.7,69.4,42.0,53.7,61.9]],["Pan Molde Blanco",[288043,267951,203126,278207,260337,262667,284628,255671,384354,438590,436090,389660,424363],[46.0,43.0,32.0,45.0,42.0,41.0,47.0,43.0,56.0,64.0,64.0,54.0,60.0]],["Sorrentinos de Jamon y Queso",[730382,362297,59500,215900,287876,69700,277297,125800,341897,200319,79338,175297,236497],[62.0,26.0,4.0,14.0,23.0,5.0,22.0,9.0,26.0,14.0,7.0,14.0,18.0]],["Sorrentinos de Ternera y Verduras",[591445,236947,190400,275189,255197,188700,219117,138550,316397,13600,264933,61200,223740],[50.0,18.0,13.0,18.0,20.0,12.0,18.0,9.0,24.0,1.0,23.0,4.0,14.0]],["Pan de Campo 450gr",[153940,152167,141424,105780,174580,139178,180494,106260,191450,142080,177108,256320,221280],[21.0,20.0,21.0,14.0,23.0,19.0,25.0,15.0,24.0,17.0,21.0,30.0,25.0]],["Sandwich de Miga Jamon y Queso",[169200,107700,115235,64800,105000,90402,91200,165402,260075,295100,194694,69550,258050],[31.0,21.0,23.0,12.0,20.0,18.0,17.0,33.0,46.0,49.0,34.0,12.0,43.0]],["FACTURAS X 2 BOLSITA",[93375,136938,105250,128500,108250,90000,276750,137000,152190,215020,157170,163680,163680],[40.0,58.0,45.0,55.0,46.0,38.0,118.0,59.0,58.0,76.0,55.0,57.0,55.0]],["pan de campo",[215860,101707,127280,97180,189093,145340,137600,113975,140381,138240,167880,117120,206400],[30.0,15.0,18.0,14.0,25.0,20.0,20.0,16.0,20.0,17.0,21.0,14.0,23.0]],["Sorrentinos de Calabaza",[202300,94400,323000,256489,68000,170000,81600,141100,150345,15300,79280,122000,193800],[13.0,6.0,21.0,17.0,5.0,11.0,6.0,9.0,11.0,1.0,6.0,8.0,12.0]],["Pan de Lomo x2",[291827,98615,84840,110967,140243,89623,123982,36862,68447,240433,77595,139754,218362],[150.0,48.0,44.0,56.0,71.0,46.0,64.0,18.0,30.0,100.0,36.0,62.0,90.0]],["Pizzetas x2",[152250,102500,130000,125000,98500,136640,56500,128806,165513,160800,92300,140026,97800],[68.0,48.0,60.0,56.0,46.0,64.0,26.0,60.0,68.0,62.0,40.0,58.0,36.0]],["Cuadrado de Limon",[159863,117723,111557,84000,92112,76500,80500,134887,121600,136000,113512,159558,150900],[38.0,27.0,28.0,19.0,21.0,17.0,18.0,34.0,30.0,30.0,27.0,40.0,34.0]],["Budin de Limon",[168800,34400,65289,36800,120000,126578,135200,156760,114400,149900,55850,286257,44500],[24.0,5.0,10.0,5.0,16.0,18.0,19.0,26.0,16.0,20.0,8.0,43.0,6.0]],["Pizza de Muzzarella",[230250,121698,75750,108750,145500,70500,90000,97875,117000,60000,84750,164250,83250],[34.0,19.0,11.0,15.0,25.0,10.0,14.0,17.0,17.0,9.0,13.0,25.0,12.0]],["Cuadrado de Coco con Dulce de Leche",[173986,48950,108595,96495,104105,49959,59950,133043,81400,129502,98689,168207,150150],[38.0,10.0,23.0,20.0,22.0,11.0,12.0,32.0,18.0,28.0,22.0,40.0,31.0]],["Postre (Lingote) Mini Marquise",[216164,117262,60447,106920,169126,56266,6930,113785,66771,159506,40811,43560,155437],[32.0,14.0,8.0,12.0,19.0,7.0,1.0,15.0,8.0,21.0,5.0,5.0,22.0]]]}};
const MERMA = {"top":[["Medialunas","UN",false,1427.3,1529.0,0.0,11.4,1502,1502,0,1058410,0,1058410],["Cuadrado de Brownie","UN",false,48.9,25.2,48.4,59.9,4403,4403,451685,558525,451685,558525],["Pan de Campo 450gr","UN",false,59.5,49.2,17.2,23.0,7985,7985,352932,472306,352932,472306],["Chipa","KG",true,45.5,57.1,0.0,11.4,28000,8964,0,628957,0,201349],["Pan de Pancho x2","UN",false,50.5,16.8,66.7,69.9,1989,1989,289974,303762,289974,303762],["Criollos","KG",true,43.0,47.8,0.0,12.5,20000,7125,0,467020,0,166375],["Pan Molde Blanco","UN",false,57.9,52.6,9.0,14.4,7028,7028,159130,253541,159130,253541],["Budin de Naranja","UN",false,17.1,11.5,32.9,39.5,7021,7021,171908,206137,171908,206137],["Cuadrado de Naranja","UN",false,20.8,13.2,36.3,52.5,4300,4300,140671,203554,140671,203554],["Cuadrado de Coco con Dulce de Leche","UN",false,28.5,21.1,26.0,34.6,4483,4483,143757,191838,143757,191838],["Pan Molde Delactosado","UN",false,13.8,9.7,30.1,44.6,6790,6790,122842,181689,122842,181689],["Pan Hamburguesa x2","UN",false,39.3,29.6,24.8,37.2,2632,2632,111197,166510,111197,166510],["Budin de Naranja sin Lactosa","UN",false,7.0,3.9,44.6,65.4,7450,7450,100885,147696,100885,147696],["Pizza de Muzzarella","UN",false,22.8,21.2,7.2,29.0,6704,6704,47932,192456,47932,192456],["Masas Pan Frances","KG",true,80.1,93.8,0.0,3.6,18000,5958,0,227832,0,75413]],"rest":[932941,4558844,932941,4558844],"nrest":55,"gw":{"43":[["2026-01-05",50.0,75.8],["2026-01-12",50.0,66.9],["2026-01-19",75.0,83.1],["2026-01-26",50.0,93.1],["2026-02-02",100.0,102.3],["2026-02-09",100.0,122.3],["2026-02-16",50.0,89.6],["2026-02-23",25.0,83.1],["2026-03-02",25.0,84.6],["2026-03-09",60.0,80.8],["2026-03-16",75.0,72.6],["2026-03-23",0.0,42.7],["2026-03-30",50.0,52.3],["2026-04-06",50.0,41.6],["2026-04-13",50.0,37.2],["2026-04-20",100.0,36.8],["2026-04-27",25.0,33.9],["2026-05-04",50.0,39.4],["2026-05-11",0.0,41.2],["2026-05-18",50.0,51.8],["2026-05-25",25.0,34.1],["2026-06-01",75.0,28.1],["2026-06-08",50.0,46.8],["2026-06-15",0.0,41.2],["2026-06-22",50.0,25.0],["2026-06-29",50.0,50.9],["2026-07-06",50.0,64.7],["2026-07-13",50.0,49.0],["2026-07-20",50.0,51.7],["2026-07-27",25.0,36.5],["2026-08-03",0.0,29.3],["2026-08-10",16.0,30.0],["2026-08-17",40.0,36.8],["2026-08-24",50.0,48.5],["2026-08-31",0.0,48.1],["2026-09-07",100.0,70.8],["2026-09-14",6.0,63.4],["2026-09-21",50.0,64.5],["2026-09-28",50.0,65.7],["2026-10-05",50.0,67.3]],"25":[["2026-01-05",60.0,70.0],["2026-01-12",60.0,69.6],["2026-01-19",60.0,60.4],["2026-01-26",60.0,71.8],["2026-02-02",60.0,68.9],["2026-02-09",100.0,77.4],["2026-02-16",60.0,68.9],["2026-02-23",60.0,68.5],["2026-03-02",20.0,64.0],["2026-03-09",40.0,70.1],["2026-03-16",60.0,72.9],["2026-03-23",40.0,38.1],["2026-03-30",20.0,38.9],["2026-04-06",40.0,29.1],["2026-04-13",60.0,30.9],["2026-04-20",40.0,31.8],["2026-04-27",40.0,28.8],["2026-05-04",40.0,29.1],["2026-05-11",0.0,30.5],["2026-05-18",60.0,37.8],["2026-05-25",20.0,36.2],["2026-06-01",40.0,38.1],["2026-06-08",60.0,34.2],["2026-06-15",0.0,33.9],["2026-06-22",40.0,32.4],["2026-06-29",60.0,34.6],["2026-07-06",40.0,38.4],["2026-07-13",60.0,59.0],["2026-07-20",40.0,37.9],["2026-07-27",40.0,25.4],["2026-08-03",20.0,35.8],["2026-08-10",40.0,35.4],["2026-08-17",40.0,31.2],["2026-08-24",40.0,34.7],["2026-08-31",20.0,46.8],["2026-09-07",40.0,66.7],["2026-09-14",20.0,69.9],["2026-09-21",40.0,43.2],["2026-09-28",20.0,58.1],["2026-10-05",60.0,63.9]],"48":[["2026-01-05",96.0,104.7],["2026-01-12",130.0,129.5],["2026-01-19",110.0,110.1],["2026-01-26",110.0,104.7],["2026-02-02",110.0,121.9],["2026-02-09",135.0,134.2],["2026-02-16",90.0,114.4],["2026-02-23",115.0,95.8],["2026-03-02",105.0,82.0],["2026-03-09",90.0,105.1],["2026-03-16",75.0,85.8],["2026-03-23",95.0,86.8],["2026-03-30",95.0,92.5],["2026-04-06",70.0,83.0],["2026-04-13",55.0,69.0],["2026-04-20",50.0,71.6],["2026-04-27",93.0,74.1],["2026-05-04",90.0,75.8],["2026-05-11",70.0,88.7],["2026-05-18",90.0,98.3],["2026-05-25",65.0,67.1],["2026-06-01",90.0,87.3],["2026-06-08",70.0,91.6],["2026-06-15",20.0,77.2],["2026-06-22",75.0,79.9],["2026-06-29",110.0,93.5],["2026-07-06",75.0,119.3],["2026-07-13",85.0,106.7],["2026-07-20",90.0,85.0],["2026-07-27",70.0,84.6],["2026-08-03",40.0,60.7],["2026-08-10",55.0,97.3],["2026-08-17",65.0,86.9],["2026-08-24",90.0,96.7],["2026-08-31",45.0,87.3],["2026-09-07",30.0,89.5],["2026-09-14",45.0,100.6],["2026-09-21",60.0,106.3],["2026-09-28",60.0,93.1],["2026-10-05",90.0,114.2]]}}; // top: [nombre, unidad, granel, prod/sem, vend/sem, %bajo, %alto, precio inf, precio caja, bajo, alto, bajo caja, alto caja]
const GRANEL = [['Chipa', 57.1, 28000, 8964], ['Criollos', 47.8, 20000, 7125], ['Pan Francés', 93.8, 18000, 5958]];
const VALOR_PRODUCIDO_MES = 39676882;
let precioBase = 'inf';
const PROY = [['2026-10',42228760,33404741,51052780],['2026-11',43943794,35119775,52767814],['2026-12',44016794,35192775,52840813],
  ['2027-01',46196552,37372533,55020571],['2027-02',68534405,59710386,77358424],['2027-03',57247554,48423535,66071573]];

const KPIS = [
  ['Ventas', 399354819, 274028883, ARSM],
  ['Unidades', 121947.6, 117159.4, NUM],
  ['Tickets', 27566, 24175, NUM],
  ['Ticket promedio', 14487, 11335, ARS],
  ['Precio medio por unidad', 3275, 2339, ARS]
];

const STRATS = [
  { t: 'Recuperar a los mayoristas que dejaron de comprar', p: 'alta', imp: 17.5,
    dato: 'Dulce Miga compraba cada 2,1 días (≈ $1,46 M/mes) y no compra desde el 17/06. Otros 4 clientes llevan más de 90 días sin comprar.',
    acc: 'Visita comercial en las próximas 2 semanas, con oferta de reactivación (bonificación en el primer pedido y condiciones de pago). Alerta automática a los 15 días sin compra.',
    impTxt: 'Solo Dulce Miga ≈ $17,5 M/año', kpi: 'Clientes reactivados; facturación mayorista mensual' },
  { t: 'Frenar la pérdida de tickets en Villa Allende', p: 'alta', imp: 15.5,
    dato: '3er trimestre: −293 tickets (−9,8%) y −15,7% de unidades contra 2025. Ticket promedio de $13.200.',
    acc: 'Relevar precios de la competencia cercana, lanzar tarjeta de sellos (la 10ª compra con descuento) y promo en los días de menor venta.',
    impTxt: 'Recuperar esos tickets ≈ $15,5 M/año', kpi: 'Tickets mensuales de Villa Allende, interanual' },
  { t: 'Sumar un segundo producto en caja', p: 'alta', imp: 8.8,
    dato: '40% de los tickets de mostrador lleva un solo producto ($6.060). Con dos productos el ticket sube a $10.424.',
    acc: 'Sugerencia activa en caja ("¿le sumo un alfajor o un budín?"), exhibidor de impulso junto a la caja y precio especial al llevar el segundo producto.',
    impTxt: 'Si 15% de esos tickets suma uno: ≈ $8,8 M/año', kpi: '% de tickets con un solo producto; unidades por ticket' },
  { t: 'Combo desayuno: café + medialunas', p: 'media', imp: 8.0,
    dato: 'Medialunas es el n°1 (18% de las ventas del trimestre) pero perdió 10% de tickets. En el mostrador se lleva con Criollos (2.060 tickets) y con café con leche (228). El café está en solo el 7,9% de los tickets. En Villa Allende, el combo café + 2 medialunas duplicó sus unidades en las últimas 4 semanas.',
    acc: 'Combo café + 2 medialunas a precio cerrado de 9 a 11 h de lunes a viernes. Cartel visible desde la vereda.',
    impTxt: 'Café al 15% de los tickets: ≈ $8 M/año', kpi: '% de tickets con café; tickets de 9 a 11 h' },
  { t: 'Packs de mostrador con los pares que más se repiten', p: 'media', imp: 4,
    dato: 'Solo mostrador, sin Dietética: los Cuadrados se compran surtidos (5 pares, 448 tickets, de 4,6 a 8,6 veces más que el azar), pero sus unidades cayeron 32%. Sorrentinos Calabaza + Ternera salen juntos en 293 tickets (56 veces más que el azar) y las dos pizzas en 119 (11 veces).',
    acc: 'Caja surtida de 4 Cuadrados, pack "Sorrentinos 2 sabores" y pack de 2 pizzas (muzzarella + jamón), exhibidos juntos y con precio cerrado algo menor que la suma.',
    impTxt: 'Recuperar la mitad de las unidades perdidas de Cuadrados ≈ $3,5 M/año, más los packs', kpi: 'Unidades de Cuadrados; tickets que incluyen cada pack' },
  { t: 'Bajar la dependencia de pocos mayoristas', p: 'media', imp: null,
    dato: '10 clientes hacen el 80% de la venta mayorista. Crimar SRL compró $36,3 M en 2026. Crecen Vikingo Foods (+159%), Productos Plin (+256%) y Pinares Resort (+284%).',
    acc: 'Plan de cuenta clave para Crimar y búsqueda de clientes parecidos a los que crecen: hoteles y gastronomía de Carlos Paz y del Valle de Calamuchita.',
    impTxt: 'Sumar 2 o 3 cuentas nuevas; no estimable', kpi: 'Facturación de clientes nuevos; peso del mayor cliente' },
  { t: 'Personal y promos según la hora', p: 'baja', imp: null,
    dato: 'Pico de tickets el sábado de 11 a 13 h y de lunes a viernes de 17 a 19 h. Lunes a la mañana y domingo a la tarde, menos de la mitad.',
    acc: 'Reforzar caja y reposición en los picos. Probar una promo de lunes a la mañana y evaluar si conviene abrir el domingo a la tarde.',
    impTxt: 'Lunes a la mañana +10%: ≈ $1 M/año', kpi: 'Tickets por hora en cada franja' },
  { t: 'Ajustar la producción a lo que se vende', p: 'alta', imp: null,
    dato: 'Sobra entre $3,0 M y $9,8 M por mes en valor de venta (8% a 25% de lo producido). Del Pan de Pancho sobra 67% a 70%; del Brownie, la mitad; de Budín y Cuadrado de Naranja, 33% a 53%.',
    acc: 'Producir lo vendido la misma semana del año anterior más 10% de margen, empezando por Brownie, Pan de Pancho, Pan de Campo, Budín de Naranja y Cuadrado de Naranja. Registrar la merma diaria por producto y cargar la producción todos los días, sobre todo de Chipa y Francés.',
    impTxt: 'Hasta ≈ $1,1 M/mes en valor de venta en esos 5 productos (el ahorro real es el costo de insumos)', kpi: '% de sobrante semanal por producto; días con producción cargada' },
  { t: 'Revisar los productos en caída', p: 'baja', imp: null,
    dato: 'Unidades del 3er trimestre: Pan Sandwich −33%, Cuadrados −32%, Cookies −49% y Tortas −60%. 56 de 470 productos hacen el 80% de las ventas.',
    acc: 'Revisar precio y exhibición de Pan Sandwich y Cuadrados, y depurar la lista de productos con venta marginal.',
    impTxt: 'Libera espacio y producción; no estimable', kpi: 'Unidades por producto en caída' }
];

// ---- render estático ----
document.getElementById('kpis').innerHTML = KPIS.map(([l, a, b, f]) => {
  const v = (a / b - 1) * 100;
  const cls = l.startsWith('Precio') ? 'flat' : v > 5 ? 'up' : v < 0 ? 'down' : 'flat';
  return `<div class="kpi"><span class="lbl">${l}</span><span class="val">${f.format(a)}</span>
    <span class="cmp"><span class="delta ${cls}">${PCT(v)}</span> contra ${f.format(b)}</span></div>`;
}).join('');

(() => {
  const max = Math.max(...HEAT.flat());
  let h = '<thead><tr><th></th>' + HORAS.map(x => `<th>${x} h</th>`).join('') + '</tr></thead><tbody>';
  HEAT.forEach((row, i) => {
    h += `<tr><th class="row">${DIAS[i]}</th>` + row.map((v, j) => {
      const closed = HORAS[j] === 14 || HORAS[j] === 15;
      const k = v / max;
      const bg = `color-mix(in oklab, var(--heat1) ${Math.round(k * 100)}%, var(--heat0))`;
      const fg = k > 0.5 ? 'var(--bg)' : 'var(--fg-2)';
      return `<td title="${DIAS[i]} ${HORAS[j]} h: ${NUM.format(v)} tickets" style="background:${bg};color:${fg}" class="${closed ? 'closed' : ''}">${closed ? '–' : NUM.format(v)}</td>`;
    }).join('') + '</tr>';
  });
  document.getElementById('heat').innerHTML = h + '</tbody>';
})();

document.getElementById('tInact').innerHTML = INACT.map(([c, d, f, g]) =>
  `<tr><td>${c}</td><td class="r">${d}</td><td class="r">${f}</td><td class="r">${ARS.format(g)}</td></tr>`).join('');
document.getElementById('tCanasta').innerHTML = CANASTA.map(([p, t, l]) =>
  `<tr><td>${p}</td><td class="r">${NUM.format(t)}</td><td class="r">${l}</td></tr>`).join('');

// ---- desperdicio ----
const mermaRow = r => precioBase === 'inf' ? { lo: r[9], up: r[10], p: r[7] } : { lo: r[11], up: r[12], p: r[8] };
function renderMerma() {
  const rest = precioBase === 'inf' ? [MERMA.rest[0], MERMA.rest[1]] : [MERMA.rest[2], MERMA.rest[3]];
  const lo = MERMA.top.reduce((s, r) => s + mermaRow(r).lo, 0) + rest[0];
  const up = MERMA.top.reduce((s, r) => s + mermaRow(r).up, 0) + rest[1];
  const g = MERMA.top.filter(r => r[2]);
  const gUp = precioBase === 'inf' ? 1323809 : 443137;
  document.getElementById('kpisMerma').innerHTML = [
    ['Pérdida estimada por mes', `${ARSM.format(lo)} – ${ARSM.format(up)}`, 'valor de venta, 70 productos'],
    ['Sobre lo producido', `${Math.round(100 * lo / VALOR_PRODUCIDO_MES)}% – ${Math.round(100 * up / VALOR_PRODUCIDO_MES)}%`, `de ${ARSM.format(VALOR_PRODUCIDO_MES)} producidos por mes`],
    ['Por año', `${ARSM.format(lo * 12)} – ${ARSM.format(up * 12)}`, 'si se mantiene el ritmo actual'],
    ['Granel (Chipa, Criollos, Francés)', `$ 0 – ${ARSM.format(gUp)}`, 'por mes, con el registro actual']
  ].map(([l, v, c]) => `<div class="kpi"><span class="lbl">${l}</span><span class="val">${v}</span><span class="cmp">${c}</span></div>`).join('');
  document.getElementById('tMerma').innerHTML = MERMA.top.map(r => {
    const m = mermaRow(r), u = r[1] === 'KG' ? ' kg' : '';
    return `<tr><td>${r[0]}${r[2] ? '<span class="tag">granel</span>' : ''}</td><td class="r">${NUM.format(r[3])}${u}</td><td class="r">${NUM.format(r[4])}${u}</td>
      <td class="r">${Math.round(r[5])}% – ${Math.round(r[6])}%</td><td class="r">${ARS.format(m.p)}${u ? '/kg' : ''}</td>
      <td class="r"><span class="range">${ARSM.format(m.lo)} – ${ARSM.format(m.up)}</span></td></tr>`;
  }).join('') + `<tr><td>Otros ${MERMA.nrest} productos</td><td class="r"></td><td class="r"></td><td class="r"></td><td class="r"></td><td class="r"><span class="range">${ARSM.format(rest[0])} – ${ARSM.format(rest[1])}</span></td></tr>`;
  document.getElementById('tGranel').innerHTML = GRANEL.map(([n, vs, pi, pc]) => {
    const p = precioBase === 'inf' ? pi : pc, kgMes = vs * 52 / 12;
    return `<tr><td>${n}</td><td class="r">${ARS.format(p)}</td>` + [0.05, 0.10, 0.15].map(x => {
      const kg = kgMes * x / (1 - x);
      return `<td class="r">${ARS.format(kg * p)}<br><span style="color:var(--muted)">${NUM.format(kg)} kg</span></td>`;
    }).join('') + '</tr>';
  }).join('') + (() => {
    const tot = x => GRANEL.reduce((s, [, vs, pi, pc]) => s + vs * 52 / 12 * x / (1 - x) * (precioBase === 'inf' ? pi : pc), 0);
    return `<tr><td><strong>Total granel</strong></td><td></td>${[0.05, 0.10, 0.15].map(x => `<td class="r"><strong>${ARS.format(tot(x))}</strong></td>`).join('')}</tr>`;
  })();
}
document.getElementById('ctlPrecio').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  precioBase = b.dataset.v;
  e.currentTarget.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
  renderMerma(); go();
});
renderMerma();

// ---- mapa de calor semanal ----
(() => {
  const LBL = { 'Todas': 'Todas', 'Carlos Paz': 'Carlos Paz', 'Villa Allende': 'Villa Allende', 'Dietetica': 'Dietética (mayorista)' };
  const st = { lugar: 'Todas', met: 'v', esc: 'fila' };
  const ctlL = document.getElementById('ctlLugar');
  Object.keys(SEMANAL.lugares).forEach((l, i) => {
    const b = document.createElement('button'); b.type = 'button'; b.id = 'lug-' + i; b.dataset.v = l;
    b.textContent = LBL[l] || l; b.setAttribute('aria-pressed', l === st.lugar); ctlL.appendChild(b);
  });
  const bind = (id, key) => document.getElementById(id).addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    st[key] = b.dataset.v;
    e.currentTarget.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    render();
  });
  bind('ctlLugar', 'lugar'); bind('ctlMet', 'met'); bind('ctlEsc', 'esc');
  const semL = SEMANAL.semanas.map(s => { const [, m, d] = s.split('-'); return `${+d}/${+m}`; });
  const fmt = x => st.met === 'v' ? NUM.format(Math.round(x / 1000)) : NUM.format(Math.round(x));
  function render() {
    const rows = SEMANAL.lugares[st.lugar].map(([n, v, u]) => [n, st.met === 'v' ? v : u]);
    const gmax = Math.max(...rows.flatMap(r => r[1]));
    let h = '<thead><tr><th class="prod">Producto · semana del</th>' + semL.map(s => `<th>${s}</th>`).join('') +
      `<th class="r">Total</th><th class="r">Últ. 4 vs prim. 4</th></tr></thead><tbody>`;
    rows.forEach(([n, vals]) => {
      const max = st.esc === 'fila' ? Math.max(...vals) : gmax;
      const a = vals.slice(0, 4).reduce((s, x) => s + x, 0), b = vals.slice(-4).reduce((s, x) => s + x, 0);
      const t = a ? (b / a - 1) * 100 : null;
      const cls = t == null ? 'flat' : t > 5 ? 'up' : t < -5 ? 'down' : 'flat';
      const arrow = t == null ? '' : t > 5 ? '▲ ' : t < -5 ? '▼ ' : '● ';
      h += `<tr><th class="prod" title="${n}">${n}</th>` + vals.map((x, j) => {
        const k = max ? x / max : 0;
        const bg = `color-mix(in oklab, var(--heat1) ${Math.round(k * 100)}%, var(--heat0))`;
        const fg = k > 0.55 ? 'var(--bg)' : 'var(--fg-2)';
        const tip = `${n} · semana del ${semL[j]}: ${st.met === 'v' ? ARS.format(x) : NUM.format(x) + ' unidades'}`;
        return `<td class="cell" title="${tip}" style="background:${bg};color:${fg}">${x ? fmt(x) : '–'}</td>`;
      }).join('') + `<td class="tot">${fmt(vals.reduce((s, x) => s + x, 0))}</td>` +
        `<td class="trend delta ${cls}">${t == null ? 'nuevo' : arrow + PCT(Math.round(t))}</td></tr>`;
    });
    document.getElementById('wheat').innerHTML = h + '</tbody>';
  }
  render();
})();
document.getElementById('strats').innerHTML = STRATS.map((s, i) => `
  <article class="strat"><div class="top"><h3>${i + 1}. ${s.t}</h3><span class="pill ${s.p}">Prioridad ${s.p}</span></div>
  <dl class="chain">
    <div><dt>Dato</dt><dd>${s.dato}</dd></div>
    <div><dt>Acción</dt><dd>${s.acc}</dd></div>
    <div><dt>Impacto estimado</dt><dd class="impact">${s.impTxt}</dd></div>
    <div><dt>KPI</dt><dd>${s.kpi}</dd></div>
  </dl></article>`).join('');

// ---- gráficos ----
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const charts = [];
function draw() {
  charts.splice(0).forEach(c => c.destroy());
  const C = { fg: css('--fg-2'), muted: css('--muted'), line: css('--line'), s1: css('--s1'), s2: css('--s2'), s3: css('--s3'), s4: css('--s4'), s5: css('--s5'), surface: css('--surface'), accent: css('--accent') };
  Chart.defaults.font.family = css('--font-body');
  Chart.defaults.color = C.fg;
  Chart.defaults.borderColor = C.line;
  const grid = { color: C.line, drawTicks: false };
  const legend = { position: 'top', align: 'start', labels: { usePointStyle: true, pointStyle: 'rectRounded', boxWidth: 10, padding: 14 } };
  const bar = { borderRadius: 4, borderSkipped: 'start', borderWidth: 0 };
  const mk = (id, cfg) => charts.push(new Chart(document.getElementById(id), cfg));

  // 1. interanual
  const m26 = MESES.filter(m => m.startsWith('2026'));
  const yoy = k => m26.map(m => +(((MENSUAL[m][k] / MENSUAL['2025' + m.slice(4)][k]) - 1) * 100).toFixed(1));
  mk('cYoy', { type: 'line', data: { labels: m26.map(ML), datasets: [
      { label: 'Ventas en pesos', data: yoy(0), borderColor: C.s1, backgroundColor: C.s1 },
      { label: 'Unidades', data: yoy(1), borderColor: C.s2, backgroundColor: C.s2 },
      { label: 'Tickets', data: yoy(2), borderColor: C.s3, backgroundColor: C.s3 } ] },
    options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      elements: { line: { borderWidth: 2, tension: 0.25 }, point: { radius: 4, hoverRadius: 6, borderWidth: 2, borderColor: C.surface } },
      plugins: { legend, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${PCT(c.parsed.y)}` } } },
      scales: { y: { grid, border: { display: false }, ticks: { callback: v => v + '%' } }, x: { grid: { display: false } } } } });

  // 2. ventas por lugar (apiladas)
  const colors = [C.s1, C.s2, C.s3, C.s4, C.s5];
  mk('cLugar', { type: 'bar', data: { labels: MESES.map(ML), datasets: LUGARES.map((l, i) => ({
      label: LUGAR_LBL[l] || l, backgroundColor: colors[i], ...bar, borderRadius: 2, borderWidth: { top: 2 }, borderColor: C.surface,
      data: MESES.map(m => (POR_LUGAR.find(r => r[0] === m && r[1] === l) || [0, 0, 0])[2]) })) },
    options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: { legend, tooltip: { callbacks: { label: c => c.parsed.y ? `${c.dataset.label}: ${ARSM.format(c.parsed.y)}` : null } } },
      scales: { x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
        y: { stacked: true, grid, border: { display: false }, ticks: { callback: v => ARSM.format(v) } } } } });

  // 3. Q3 por lugar
  const v = (a, b) => +(((a / b) - 1) * 100).toFixed(1);
  mk('cQ3', { type: 'bar', data: { labels: Q3.map(r => LUGAR_LBL[r[0]] || r[0]), datasets: [
      { label: 'Ventas en pesos', data: Q3.map(r => v(r[1], r[2])), backgroundColor: C.s1, ...bar },
      { label: 'Unidades', data: Q3.map(r => v(r[3], r[4])), backgroundColor: C.s2, ...bar },
      { label: 'Tickets', data: Q3.map(r => v(r[5], r[6])), backgroundColor: C.s3, ...bar } ] },
    options: { maintainAspectRatio: false, indexAxis: 'y', interaction: { mode: 'index', intersect: false },
      datasets: { bar: { categoryPercentage: 0.75, barPercentage: 0.9 } },
      plugins: { legend, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${PCT(c.parsed.x)}` } } },
      scales: { x: { grid, border: { display: false }, ticks: { callback: x => x + '%' } }, y: { grid: { display: false } } } } });

  // 4. categorías
  mk('cCat', { type: 'bar', data: { labels: CAT.map(r => r[0]), datasets: [
      { label: 'Ventas en pesos', data: CAT.map(r => v(r[1], r[2])), backgroundColor: C.s1, ...bar },
      { label: 'Unidades', data: CAT.map(r => v(r[3], r[4])), backgroundColor: C.s2, ...bar } ] },
    options: { maintainAspectRatio: false, indexAxis: 'y', interaction: { mode: 'index', intersect: false },
      datasets: { bar: { categoryPercentage: 0.8, barPercentage: 0.9 } },
      plugins: { legend, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${PCT(c.parsed.x)}` } } },
      scales: { x: { grid, border: { display: false }, ticks: { callback: x => x + '%' } }, y: { grid: { display: false }, ticks: { autoSkip: false } } } } });

  // 5. composición del ticket
  mk('cMix', { type: 'bar', data: { labels: MIX.map(r => r[0]), datasets: [
      { label: 'Tickets', data: MIX.map(r => r[1]), backgroundColor: MIX.map((r, i) => i === 0 ? C.s2 : C.s1), ...bar } ] },
    options: { maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => `${NUM.format(c.parsed.y)} tickets · promedio ${ARS.format(MIX[c.dataIndex][2])}` } } },
      scales: { y: { grid, border: { display: false }, ticks: { callback: x => NUM.format(x) } }, x: { grid: { display: false } } } },
    plugins: [{ id: 'lbl', afterDatasetsDraw(ch) { const { ctx } = ch; ctx.save(); ctx.fillStyle = C.fg; ctx.font = '500 12px ' + css('--font-data'); ctx.textAlign = 'center';
      ch.getDatasetMeta(0).data.forEach((b, i) => ctx.fillText('prom. ' + ARS.format(MIX[i][2]), b.x, b.y - 8)); ctx.restore(); } }] });

  // 6. proyección
  const hist = MESES.map(m => MENSUAL[m][0]);
  const labs = [...MESES, ...PROY.map(p => p[0])].map(ML);
  const pad = Array(MESES.length - 1).fill(null);
  mk('cProy', { type: 'line', data: { labels: labs, datasets: [
      { label: 'Real', data: hist, borderColor: C.s1, backgroundColor: C.s1, pointRadius: 0 },
      { label: 'Rango bajo', data: [...pad, hist.at(-1), ...PROY.map(p => p[2])], borderColor: 'transparent', pointRadius: 0, fill: false },
      { label: 'Rango', data: [...pad, hist.at(-1), ...PROY.map(p => p[3])], borderColor: 'transparent', backgroundColor: C.s2 + '33', pointRadius: 0, fill: '-1' },
      { label: 'Proyección', data: [...pad, hist.at(-1), ...PROY.map(p => p[1])], borderColor: C.s2, backgroundColor: C.s2, borderDash: [6, 4], pointRadius: 3 } ] },
    options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, elements: { line: { borderWidth: 2, tension: 0.2 } },
      plugins: { legend: { ...legend, labels: { ...legend.labels, filter: i => i.text !== 'Rango bajo' } },
        tooltip: { filter: i => i.raw != null && i.dataset.label !== 'Rango bajo' || (i.dataset.label === 'Rango bajo' && i.raw != null),
          callbacks: { label: c => `${c.dataset.label === 'Rango' ? 'Rango alto' : c.dataset.label}: ${ARSM.format(c.parsed.y)}` } } },
      scales: { y: { grid, border: { display: false }, ticks: { callback: x => ARSM.format(x) } }, x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 9 } } } } });

  // 6b. desperdicio: barras flotantes bajo–alto
  const MT = MERMA.top.slice().sort((a, b) => mermaRow(b).up - mermaRow(a).up);
  mk('cMerma', { type: 'bar', data: { labels: MT.map(r => r[0] + (r[2] ? ' (granel)' : '')), datasets: [
      { label: 'Pérdida mensual (bajo – alto)', data: MT.map(r => [mermaRow(r).lo, Math.max(mermaRow(r).up, mermaRow(r).lo + 1)]), backgroundColor: MT.map(r => r[2] ? C.s2 : C.s1), borderRadius: 4, borderSkipped: false } ] },
    options: { maintainAspectRatio: false, indexAxis: 'y',
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => { const r = MT[c.dataIndex], m = mermaRow(r);
        return [`Entre ${ARSM.format(m.lo)} y ${ARSM.format(m.up)} por mes`, `Sobra ${Math.round(r[5])}% a ${Math.round(r[6])}% de lo producido`]; } } } },
      scales: { x: { grid, border: { display: false }, ticks: { callback: x => ARSM.format(x) } }, y: { grid: { display: false }, ticks: { autoSkip: false } } } } });

  // 6c. granel: kg producidos vs vendidos
  for (const pid of ['43', '25', '48']) {
    const rows = MERMA.gw[pid];
    mk('cG' + pid, { type: 'line', data: { labels: rows.map(r => { const [, m, d] = r[0].split('-'); return `${+d}/${+m}`; }), datasets: [
        { label: 'Producido (kg)', data: rows.map(r => r[1]), borderColor: C.s1, backgroundColor: C.s1 },
        { label: 'Vendido (kg)', data: rows.map(r => r[2]), borderColor: C.s2, backgroundColor: C.s2 } ] },
      options: { maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
        elements: { line: { borderWidth: 2, tension: 0.2 }, point: { radius: 0, hoverRadius: 5 } },
        plugins: { legend: { ...legend, labels: { ...legend.labels, padding: 8 } }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${NUM.format(c.parsed.y)}` } } },
        scales: { y: { grid, border: { display: false }, beginAtZero: true }, x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 5 } } } } });
  }

  // 7. impacto
  const S = STRATS.filter(s => s.imp);
  mk('cImp', { type: 'bar', data: { labels: S.map(s => s.t), datasets: [
      { label: 'Impacto anual', data: S.map(s => s.imp), backgroundColor: C.s1, ...bar } ] },
    options: { maintainAspectRatio: false, indexAxis: 'y',
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ARSM.format(c.parsed.x * 1e6) + ' por año' } } },
      scales: { x: { grid, border: { display: false }, ticks: { callback: x => '$' + x + ' M' } },
        y: { grid: { display: false }, ticks: { callback: function (i) { const t = this.getLabelForValue(i); return t.length > 34 ? t.slice(0, 32) + '…' : t; } } } } } });
}
const go = () => { if (window.Chart) draw(); };
go();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', go);
new MutationObserver(go).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
