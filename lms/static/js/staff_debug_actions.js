// Build StaffDebug object
var StaffDebug = (function(){

  get_current_url = function() {
    return window.location.pathname;
  }

  get_url = function(action){
    var problem_to_reset = action.location;
    var unique_student_identifier = get_user(action.locationName);
    var pathname = this.get_current_url();
    var url = pathname.substr(0,pathname.indexOf('/courseware')) + '/instructor'+ '?unique_student_identifier=' + unique_student_identifier + '&problem_to_reset=' + problem_to_reset;
    return url;
  }

  get_user = function(locname){
    var uname = $('#sd_fu_' + locname).val();
    if (uname==""){
        uname =  $('#sd_fu_' + locname).attr('placeholder');
    }
    return uname;
  }

  do_idash_action = function(action){
    var instructor_tab_url = get_url(action);
    window.location = instructor_tab_url + '#view-student_admin';
  }

  reset = function(locname, location){
    this.do_idash_action({
        locationName: locname,
        location: location
    });
  }

  sdelete = function(locname, location){
    this.do_idash_action({
        locationName: locname,
        location: location
    });
  }

  rescore = function(locname, location){
    this.do_idash_action({
        locationName: locname,
        location: location
    });
  }

  return {
      reset: reset,
      sdelete: sdelete,
      rescore: rescore,
      do_idash_action: do_idash_action,
      get_current_url: get_current_url,
      get_url: get_url,
      get_user: get_user
  }
})();

// Register click handlers
$(document).ready(function() {
    var $courseContent = $('.course-content');
    $courseContent.on("click", '.staff-debug-reset', function() {
        StaffDebug.reset($(this).parent().data('location-name'), $(this).parent().data('location'));
        return false;
    });
    $courseContent.on("click", '.staff-debug-sdelete', function() {
        StaffDebug.sdelete($(this).parent().data('location-name'), $(this).parent().data('location'));
        return false;
    });
    $courseContent.on("click", '.staff-debug-rescore', function() {
        StaffDebug.rescore($(this).parent().data('location-name'), $(this).parent().data('location'));
        return false;
    });
});
