"use strict"

const RequestType = {POST: "post", GET: "get"};
const url = "http://users.jyu.fi/~jaankaup/cgi-bin/tiea2080/vt5/index.cgi/";

$(document).ready(e => init());

function init() {
  createResponse({nextState:"kirjaudu", data: {newSession: "ok"}});
}

/////////////////////////////////////////////////////////////////////////////////////////////////////

/* Funktio joka asettaa footerin tapahtumineen paikoilleen. */
function setFooter(data, textStatus, request) {
  var newNode = document.importNode(request.responseXML.documentElement,1);
  $("#footer").replaceWith(newNode);
  $("#aMuokkaaJoukkue").on('click', (e) => {e.preventDefault(); createResponse({nextState:"muokkaaJoukkue"});});
  $("#aJoukkueListaus").on('click', (e) => {e.preventDefault();createResponse({nextState:"joukkuelistaus"});});
  $("#aKirjauduUlos").on('click', (e) => {e.preventDefault();createResponse({nextState:"logoutPage"});});
  $("#aMainPage").on('click', (e) => {e.preventDefault();createResponse({nextState:"mainPage"});});
  var kNimi = getKilpailuNimi();
  $("#aRastilistaus").on('click', (e) => {e.preventDefault();createResponse({nextState:"rastilistaus",data:{kNimi:kNimi}});});
}

/////////////////////////////////////////////////////////////////////////////////////////////////////

function getKilpailuNimi() {
  try {
    return encodeURI($("#footerKilpailuNimi").get(0)['textContent']);
  }
  catch(error) {
    console.error("getKilpailuNimi: Ei loytynyt kilpailun nimea");
    console.error(error);
    return undefined;
  } 
}

/////////////////////////////////////////////////////////////////////////////////////////////////////

/* Responsen luonti funktio. */
/* Parametrit: reqType, data, nextState,dataType,success */
/* Olisi ehka voinnut muuttaa default-settingseja qjueryssa, mutta eipas sotkeuduta sellaiseen tallakertaa. */
function createResponse(requestParameters) {
	
  // Default-arvot.
  var parametrit = {reqType:RequestType.GET,
 		    data:{},
 		    nextState:"",
 		    dataType:"xml",
 		    success:checkState}; 

  // Asetetaan kutsujalta tulleet arvot.
  for (let p in requestParameters) {
    if (parametrit[p] === undefined) {
	console.debug(`createResponse: ei ${p} parametria ole olemassakaan!!!`);
    }
    else {
	parametrit[p] = requestParameters[p]; 
    }
  }

  // Vain debuggausta.
  console.log(`Creating response for ${url+parametrit['nextState']}.`);
  console.log(`Request type: ${parametrit['reqType']}.`);
  console.log(`Data:`);
  console.log(parametrit['data']);

  // Latausindikaattori paalle.
  latausIndikaattoriStart();

  // Tehdaan ajax-kutsu.
  $.ajax({ async: true,
	   url: url + parametrit['nextState'],
	   type: parametrit['reqType'],
       	   data: parametrit['data'],
     	   dataType: parametrit['dataType'],
     	   success: (d,t,r) => {latausIndikaattoriStop(); parametrit['success'](d,t,r);},
    	   error: (xhr, status, error) => {
		   console.log(`Error: ${parametrit['nextState']}.`);
		   console.log(`status = ${status}.`);
		   console.log(`error = ${error}.`);
  		   console.log(xhr.responseText);
	       latausIndikaattoriStop();
	   }});
}

/////////////////////////////////////////////////////////////////////////////////////////////////////

/* Kehno kopio pythonin quote_plus funktiosta. Toimii ainakin naennaisesti tassa sovelluksessa. 
 * Kaupalliseen sovellukseen en laittaisi. */
function myQuote_plus(str) {
  return str.split(' ').map(x => encodeURI(x)).join('+');
}

/////////////////////////////////////////////////////////////////////////////////////////////////////

function latausIndikaattoriStart() {
  $("*").css("cursor","progress");
}

/////////////////////////////////////////////////////////////////////////////////////////////////////

function latausIndikaattoriStop() {
  $("*").css("cursor", "");
}

/////////////////////////////////////////////////////////////////////////////////////////////////////

/* Funktio joka asettaa tulevan sivun tapahtuman kasittelijat paikoilleen ym. */
function checkState(data, textStatus, request) {
  var next = request.getResponseHeader('nextState'); 
  var updateFooter = request.getResponseHeader('updateFooter'); 
  if (next === null) {
    console.error("checkState: next == null");
    return
  }

//  console.debug(request.responseText);

  // Korvataan vanha content uudella.
  var newNode = document.importNode(request.responseXML.documentElement,1);
  $("#content").replaceWith(newNode);

  // Jos seuraava sivu on kirjaudu-sivu, niin ...
  if (next === "kirjaudu") {
    $("#loginButton").on('click', (e) => {
        e.preventDefault();
        createResponse({reqType:RequestType.POST, nextState:next, data: $('#loginForm').serialize()});
    });
  }


  // Jos palvelin kehoittaa kehoittaa tyhjentamaan footerin.
  if (updateFooter === "clear") $("#footer").empty();

  // Jos palvelin kehoittaa paivittamaan footerin, niin ....
  if (updateFooter === "True") { 
    createResponse({nextState:"footerResponse",success:setFooter}); 
  }

  // Muokkaa joukkue...
  if (next === "muokkaaJoukkue") {
    console.log("checkState: muokkaaJoukkue");
    $("#tallennaJoukkueButton").on("click", (e) => {
      e.preventDefault();
      createResponse({nextState:"muokkaaJoukkue",
      	        reqType: RequestType.POST,
               	data: $("form").serialize()}
      	      );
    });
    $("#lisaaTupaButton").on("click", (e) => {
      e.preventDefault();
      createResponse({nextState:"muokkaaTupa",
               	data: {jNimi:myQuote_plus($("#jNimiHidden").get(0)['value']),aika:"",koodi:""}}
      	      );
    });

    // Kokeillaan laittaa muokkaaTupaan tapahtuma (admin tilassa toimii).
    // Muuten saadaan poikkeus eika elama siihen kaadu...
    try {
      $(".rastiTr").each((i,elem) => {
        	var tr = $(elem);
        	var aikaElem = tr.find("td .aTupa");
        	var aika = aikaElem.get(0)['textContent'];    
        	var koodi = tr.find(".tdKoodi").get(0)['textContent'];    
        	aikaElem.on('click', (e) => {
        	  e.preventDefault();
        	  createResponse({nextState:"muokkaaTupa",
        	                  data: {jNimi:$("#jNimiHidden").get(0)['value'], 
        	                         aika:myQuote_plus(aika),
        	                         koodi:myQuote_plus(koodi)}});
        	});
    });
    } catch(error) { ; }
    return;
  }
  
  // Kirjaudu ulos...
  if (next === "logout") {
    $("#logoutButton").on('click', (e) => {
      e.preventDefault();
      createResponse({nextState:"kirjaudu", data: {newSession: "ok"}});
    });
  }

  // Paasivu...
  if (next === "mainPage") {
    console.log("checkState: mainPage");
    $(".kilpailuLi").each((i,elem) => {
      $(elem).on('click', (e) => {
	e.preventDefault();
	createResponse({nextState:"muokkaaKisa", data: {kNimi:encodeURI(elem.textContent)}})
      });
    });
  }

  // Rastilistaus sivu...
  if (next === "rastilistaus") {
    console.log("checkState: rastilistaus");
    $("#tallennaRasti").on('click', (e) => {
	e.preventDefault();
	createResponse({nextState:"rastilistaus",
		        reqType: RequestType.POST,
	         	data: $("form").serialize()}
		      )
        });
    
    $(".rastilistausMuokkaa").each((i,elem) => {
      $(elem).on('click', (e) => {
	e.preventDefault();
	createResponse({nextState:"rastilistaus",
	         	data: {kNimi:getKilpailuNimi(),index:i}
	                });
	$('html,body').animate({scrollTop: $("form").offset().top},'fast');

      });
    });
  }
  

  // Muokkaa kisa sivu...
  if (next === "muokkaaKisa") {
    var kNimi = getKilpailuNimi();
    $("#pRastilistaus2").on('click', (e) => createResponse({nextState:"rastilistaus",data:{kNimi:kNimi}}));
    $("#tallennaSarja").on('click', (e) => {
		    e.preventDefault();
		    createResponse({nextState:"muokkaaKisa",
			            data:$("form").serialize(),
		                    reqType:RequestType.POST});});

    $(".sarjaLi").each((i,elem) => {
      $(elem).on('click', (e) => {
	e.preventDefault();
	createResponse({nextState:"muokkaaSarja",
	         	data: {kNimi:getKilpailuNimi(),sNimi:encodeURIComponent(elem.textContent)}
	                });
      });
    });
    
  }

  // Muokkaa sarja sivu... On muuten aika selkeita ja kauniita nama lambda lausekkeet :).
  if (next === "muokkaaSarja") {
    
    $(".aJoukkue").each((i,elem) => {
      $(elem).on('click', (e) => {
	e.preventDefault();
	createResponse({nextState:"muokkaaJoukkue",
	         	data: {jNimi:encodeURIComponent(elem.textContent)}
	                });
      });
    });

    $("#tallennaJoukkue").on('click', (e) => {
		    e.preventDefault();
		    createResponse({nextState:"muokkaaSarja",
			            data:$("form").serialize(),
		                    reqType:RequestType.POST});});
  }

  // Muokkaa tupa sivu...
  if (next === "muokkaaTupa") {
    $("#tallennaTupa").on('click', (e) => {
		    e.preventDefault();
		    createResponse({nextState:"muokkaaTupa",
			            data:$("form").serialize(),
		                    reqType:RequestType.POST});});
  }
}
