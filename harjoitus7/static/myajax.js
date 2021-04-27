'use strict';

var url = window.location.origin + "/suosikit"
$(document).ready(e => init());

// Globaali muuttuja sille, etta naytetaanko suosikit vai ei. Laiskuus ja
// kiire... Sielta mennaan missa aita on matalaa.
var nayta = true;

// Globaali muuttuja sille, naytetaanko kaikki syotteet vai ainoastaan
// kayttajan syotteet.
var nayta_kaikki = false;

/***********************************************************************************************************************/

function init() {

    var uutisUL = $('.uutis_ul');

    // Sallitaan jarjestyksen vaihto ainoastaan suosikit sivulle.
    if (window.location.toString() === url) {
      uutisUL.sortable({stop: updateOrder});
      uutisUL.disableSelection();
    }

    var suosikkinappi = $('.suosikki');
    suosikkinappi.on('click', toggle_nappi);

    var ei_suosikkinappi = $('.ei_suosikki');
    ei_suosikkinappi.on('click', toggle_nappi);
        
    var naytaNappi = $('#naytaSuosikit');
    naytaNappi.on('click',toggle_nayta);

    // Vahan kehnoa meinikia, mutta kiireetta pittaa.
    var poistaNappi = $('.tuhoaNappi');
    poistaNappi.on('click', tuhoaSuosikki);

    var toggleSyotteet = $('#toggleSyotteet');
    toggleSyotteet.on('click', toglaaSyotteet);

    var kaikki = $('.allSyote');
    kaikki.hide();
}

/***********************************************************************************************************************/

function parsiUutinen(jquery_element) {
    var otsikko = jquery_element.find(".otsikko").text();
    var kuvaus = jquery_element.find(".kuvaus").text();
    var linkki = jquery_element.find(".linkki").attr('href');
    var data = {title: otsikko, description: kuvaus, link: linkki};
    return data;
}

/***********************************************************************************************************************/

function toggle_nappi(e) {
    var jquery_e = $(e.target);
    var old_class = jquery_e.attr("class");
    var command = undefined;
    if (old_class == "suosikki") {
        e.target.className = "ei_suosikki";
        e.target.textContent = "ei_suosikki";
        command = "DELETE";
    }
    else {
        e.target.className = "suosikki";
        e.target.textContent = "suosikki";
        command = "NEW";
    }

    var data = [parsiUutinen($(e.target).parent())];
    data = {command: command, data: data}
    var error = ajaxPutSuosikki(data);
    if (error = "") console.log("Onnistu");
    else console.log(error);
}

/***********************************************************************************************************************/

function toggle_nayta(e) {
    nayta = !nayta;
    var eiSuosikit = $('.ei_suosikki').parent()
    if (nayta) {
      eiSuosikit.hide();
    }
    else {
      eiSuosikit.show();
    }
}

/***********************************************************************************************************************/

function tuhoaSuosikki(e) {
    console.log("tuhotaan suosikki.");
    var data = [parsiUutinen($(e.target).parent(),"DELETE")];
    data = {command: 'DELETE', data: data}
    ajaxPutSuosikki(data);

    // Vahan riskaa pelia, mutta ei voi oikein jquery when/then ovat
    // asynkronisia. Niista on vaikeahko saada status koodia jos ei sitten 
    // ala pelleilemaan callback tyyliin. En taida nyt alkaa siihen
    // ajanpuutteen vuoksi...
    $(e.target).parent().remove();
}

/***********************************************************************************************************************/

// Lahetetaan palvelimelle suosikin lisays- tai poistopyynto.
// Kaytetaan laiskuuden vuoksi put-metodia.
function ajaxPutSuosikki(data) {
    $.when($.ajax({ async: true,
                    url: url,
                    type: "put",
                    dataType:"json",
                    data: JSON.stringify(data),
                    contentType: 'application/json'}))
      .then(() => {}, (x,t,e) => { console.log(x.status);});
}

/***********************************************************************************************************************/

function updateOrder(e) {
  //e.preventDefault();
  var listItems = $('.uutis_palkki')
  var data = []
  listItems.each((i,e) => {
    console.log(e);
    data.push(parsiUutinen($(e)));
    });
  data = {command: 'UPDATE', data:data}
  var error = ajaxPutSuosikki(data);
  if (error = "") console.log("Onnistu");
  else console.log(error);
}

/***********************************************************************************************************************/

function toglaaSyotteet(e) {
    nayta_kaikki = !nayta_kaikki;
    var omat = $('.omaSyote'); //.parent();
    var kaikki = $('.allSyote'); //.parent();
    if (nayta_kaikki) {
      e.target.textContent = "Näytä omat syötteet";
      omat.hide();
      kaikki.show();
    }
    else {
      e.target.textContent = "Näytä kaikki syötteet";
      omat.show();
      kaikki.hide();
    }
}

