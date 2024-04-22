<h4> 
    Comments 
</h4>
<br />
{% if comments %}
<ul class="list-group list-group-flush">
    {% for comment in comments %}
    <li class="list-group-item">
        <div>
            {{ comment.add_time | formatdatetimedisplay }}
            <div class="position-absolute top-0 end-0 d-print-none">
                <button type="button" class="btn btn-light" id="editcommentbtn" onclick="initiateeditcomment('{{comment.key}}')">
                <i class="bi-pen"></i>
                </button>
                <button type="button" class="btn btn-light"  id="deletecommentbtn" onclick="deletecomment('{{comment.key}}')">
                <i class="bi-trash"></i>
            </button>
            </div>
            {% if allcomments %}
                <span class="badge bg-light text-dark">{{comment.badge}}</span>
            {% endif %}
        </div>
        <div>
            {%if comment.title %}
            <div>
                <b>
                    {{ comment.title }}
                </b>
            </div>
            {% endif %}
            <div id="{{comment.key}}">
                {{ comment.text | safe}}
            </div>
            <button type="button" class="btn btn-light d-none" id="editcommentbtn" onclick="editcomment('{{comment.key}}')" hidden>
                <i class="bi-truck"></i>
            </button>
        </div>
    </li>
    {% endfor %}
</ul>
<div class="d-print-none">
    {{ pagination.links }}
</div>
{% else %}
<p>No comments available.</p>
<br />
{% endif %}
<h5 class="d-print-none"> 
Post a comment 
</h5>
<form class="d-print-none" action="" method="post" role="form" id="commentform">
    <div class="form-group">
        <div class="input text">
            <label for="title">Title:</label>
            <input id="commenttitlebox" class="form-control" name="title" type="text" value="">
        </div>
        <div class="input text">
            <label for="text">Text:</label>
            <textarea id="commentbox" class="form-control" name="text" required></textarea>
        </div>
    </div>
    <button type="submit" class="btn btn-success" id="postcommentbutton">Post Comment</button>
</form>
    <script type="text/javascript" src="/static/scripts/ckeditor.js"></script>
    <script type="text/javascript">
        window.editor = null;
        ClassicEditor
            .create( document.querySelector( '#commentbox' ), { 
                simpleUpload: {
                    // The URL that the images are uploaded to.
                    uploadUrl: '/images',
                }}
            )
            .then( newEditor => {
                window.editor = newEditor;
            } )
            .catch( error => {
                console.error( error );
            } );
        $("#postcommentbutton").click(function(event){        
                event.preventDefault();
                $.post("comments", {"title":$("#commenttitlebox").val(), "text":editor.getData()}, function(data) {
                $("#commentform")[0].reset();
                window.location.reload();
            }, "json");
            });   

        function initiateeditcomment(commentid){
            ClassicEditor.replace(commentid);
        }
        function editcomment(commentid){
                $.post("comments/" + commentid, 
                                {"title":$("#commenttitlebox").val(), "text":editor.getData()}, 
                                function(data) {
                                    window.location.reload();
                                }, "json");
                }   

        function deletecomment(commentid){
                $.ajax({
                            url:"comments/" + commentid,
                            type:"DELETE", 
                            success: function(data) {
                                        window.location.reload();
                                    }
                    });
            }

    </script>
